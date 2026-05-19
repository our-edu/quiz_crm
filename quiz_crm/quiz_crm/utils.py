import re

import frappe
from frappe import _
from frappe.utils import cint, flt

RE_SLUG_NOTALLOWED = re.compile("[^a-z0-9]+")


def get_lms_path():
	path = frappe.conf.get("lms_path") or "lms"
	return path.strip("/")


def get_lms_route(path=""):
	base = f"/{get_lms_path()}"
	if not path:
		return base
	return f"{base}/{path.lstrip('/')}"


def slugify(title: str, used_slugs: list = None):
	"""Converts title to a slug.

	If a list of used slugs is specified, it will make sure the generated slug
	is not one of them.

		>>> slugify("Hello World!")
		'hello-world'
		>>> slugify("Hello World!", ["hello-world"])
		'hello-world-2'
		>>> slugify("Hello World!", ["hello-world", "hello-world-2"])
		'hello-world-3'
	"""
	if not used_slugs:
		used_slugs = []

	slug = RE_SLUG_NOTALLOWED.sub("-", title.lower()).strip("-")
	used_slugs = set(used_slugs)

	if slug not in used_slugs:
		return slug

	count = 2
	while True:
		new_slug = f"{slug}-{count}"
		if new_slug not in used_slugs:
			return new_slug
		count = count + 1


def generate_slug(title: str, doctype: str):
	result = frappe.get_all(doctype, fields=["name"])
	slugs = {row["name"] for row in result}
	return slugify(title, used_slugs=slugs)


def get_chapters(course: str):
	"""Returns all chapters of this course."""
	if not course:
		return []
	chapters = frappe.get_all("Chapter Reference", {"parent": course}, ["idx", "chapter"], order_by="idx")
	for chapter in chapters:
		chapter_details = frappe.db.get_value(
			"Course Chapter",
			{"name": chapter.chapter},
			["name", "title"],
			as_dict=True,
		)
		if chapter_details:
			chapter.update(chapter_details)
	return chapters


def get_lessons(course: str, chapter: str = None, get_details: bool = True, progress: bool = False):
	"""If chapter is passed, returns lessons of only that chapter.
	Else returns lessons of all chapters of the course"""
	lessons = []
	lesson_count = 0
	if chapter:
		if get_details:
			return get_lesson_details(chapter, progress=progress)
		else:
			return frappe.db.count("Lesson Reference", {"parent": chapter.name})

	for chapter in get_chapters(course):
		if get_details:
			lessons += get_lesson_details(chapter, progress=progress)
		else:
			lesson_count += frappe.db.count("Lesson Reference", {"parent": chapter.name})

	return lessons if get_details else lesson_count


def get_lesson_details(chapter: dict, progress: bool = False):
	lessons = []
	lesson_list = frappe.get_all(
		"Lesson Reference", {"parent": chapter.name}, ["lesson", "idx"], order_by="idx"
	)
	for row in lesson_list:
		lesson_details = frappe.db.get_value(
			"Course Lesson",
			row.lesson,
			[
				"name",
				"title",
				"include_in_preview",
				"body",
				"creation",
				"youtube",
				"quiz_id",
				"question",
				"file_type",
				"instructor_notes",
				"course",
				"chapter",
				"content",
			],
			as_dict=True,
		)
		if lesson_details:
			lesson_details.number = f"{chapter.idx}-{row.idx}"
			if progress:
				lesson_details.is_complete = get_progress(lesson_details.course, lesson_details.name)
			lessons.append(lesson_details)
	return lessons


def get_progress(course: str, lesson: str):
	return frappe.db.exists(
		"LMS Course Progress",
		{"course": course, "lesson": lesson, "member": frappe.session.user, "status": "Complete"},
	)


def get_lesson_count(course: str) -> int:
	lesson_count = 0
	chapters = frappe.get_all("Chapter Reference", {"parent": course}, ["chapter"])
	for chapter in chapters:
		lesson_count += frappe.db.count("Lesson Reference", {"parent": chapter.chapter})
	return lesson_count


def get_course_progress(course: str, member: str = None):
	"""Returns the course progress of the session user"""
	lesson_count = get_lessons(course, get_details=False)
	if not lesson_count:
		return 0
	completed_lessons = frappe.db.count(
		"LMS Course Progress",
		{"course": course, "member": member or frappe.session.user, "status": "Complete"},
	)
	precision = cint(frappe.db.get_default("float_precision")) or 3
	return flt(((completed_lessons / lesson_count) * 100), precision)


def recalculate_course_progress(course: str, member: str):
	progress = get_course_progress(course, member)
	membership = frappe.db.get_value(
		"LMS Enrollment",
		{
			"member": member,
			"course": course,
		},
		"name",
	)
	if membership:
		frappe.db.set_value("LMS Enrollment", membership, "progress", progress)


def is_demo_course(course: str) -> bool:
	title = frappe.db.get_value("LMS Course", course, "title")
	return title == "A guide to Frappe Learning"


def get_instructors(doctype: str, docname: str):
	instructor_details = []
	instructors = frappe.get_all(
		"Course Instructor",
		{"parent": docname, "parenttype": doctype},
		order_by="idx",
		pluck="instructor",
	)

	for instructor in instructors:
		instructor_details.append(
			frappe.db.get_value(
				"User",
				instructor,
				["name", "username", "full_name", "user_image", "first_name"],
				as_dict=True,
			)
		)
	return instructor_details


def get_average_rating(course: str):
	reviews = frappe.get_all(
		"LMS Course Review",
		{"course": course},
		["rating"],
	)
	ratings = [r.rating for r in reviews]
	if not len(ratings):
		return None
	return sum(ratings) / len(ratings)


def has_course_instructor_role(member: str = None):
	return frappe.db.get_value(
		"Has Role",
		{"parent": member or frappe.session.user, "role": "Course Creator"},
		"name",
	)


def has_moderator_role(member: str = None):
	return frappe.db.get_value(
		"Has Role",
		{"parent": member or frappe.session.user, "role": "Moderator"},
		"name",
	)


def validate_image(path: str) -> str:
	if path and "/private" in path:
		frappe.db.set_value(
			"File",
			{"file_url": path},
			"is_private",
			0,
		)
		return path.replace("/private", "")
	return path


def get_evaluator(course: str, batch: str = None):
	evaluator = None
	if batch:
		evaluator = frappe.db.get_value(
			"Batch Course",
			{"parent": batch, "course": course},
			"evaluator",
		)
	else:
		evaluator = frappe.db.get_value("LMS Course", course, "evaluator")
	return evaluator


def update_payment_record(doctype: str, docname: str):
	"""Placeholder - payment integration not available in quiz_crm standalone."""
	pass
