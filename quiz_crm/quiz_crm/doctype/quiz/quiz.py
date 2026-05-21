# Copyright (c) 2021, FOSS United and contributors
# For license information, please see license.txt

import json
import re
from binascii import Error as BinasciiError

import frappe
from frappe import _, safe_decode
from frappe.core.doctype.file.utils import get_random_filename
from frappe.model.document import Document
from frappe.utils import cint, comma_and, cstr, flt
from frappe.utils.file_manager import safe_b64decode
from fuzzywuzzy import fuzz

from quiz_crm.quiz_crm.doctype.course_lesson.course_lesson import save_progress
from quiz_crm.quiz_crm.utils import (
	generate_slug,
)


class Quiz(Document):
	def validate(self):
		self.validate_duplicate_questions()
		self.validate_limit()
		self.calculate_total_marks()
		self.validate_open_ended_questions()

	def validate_duplicate_questions(self):
		questions = [row.question for row in self.questions]
		rows = [i + 1 for i, x in enumerate(questions) if questions.count(x) > 1]
		if len(rows):
			frappe.throw(_("Rows {0} have the duplicate questions.").format(frappe.bold(comma_and(rows))))

	def validate_limit(self):
		if not self.shuffle_questions and self.limit_questions_to:
			self.limit_questions_to = 0

		if self.limit_questions_to and cint(self.limit_questions_to) >= len(self.questions):
			frappe.throw(_("Limit cannot be greater than or equal to the number of questions in the quiz."))

		if self.limit_questions_to and cint(self.limit_questions_to) < len(self.questions):
			marks = [question.marks for question in self.questions]
			if len(set(marks)) > 1:
				frappe.throw(_("All questions should have the same marks if the limit is set."))

	def calculate_total_marks(self):
		if len(self.questions) == 0:
			self.total_marks = 0
			self.passing_percentage = 100
			return

		if self.limit_questions_to:
			self.total_marks = sum(
				question.marks for question in self.questions[: cint(self.limit_questions_to)]
			)
		else:
			self.total_marks = sum(cint(question.marks) for question in self.questions)

	def validate_open_ended_questions(self):
		types = [question.type for question in self.questions]
		types = set(types)

		if "Open Ended" in types:
			if len(types) > 1:
				frappe.throw(
					_(
						"If you want open ended questions then make sure each question in the quiz is of open ended type."
					)
				)
			else:
				self.show_answers = 0

	def autoname(self):
		if not self.name:
			self.name = generate_slug(self.title, "Quiz")

	def get_last_submission_details(self):
		"""Returns the latest submission for this user."""
		user = frappe.session.user
		if not user or user == "Guest":
			return

		result = frappe.get_all(
			"Quiz Submission",
			fields="*",
			filters={"owner": user, "quiz": self.name},
			order_by="creation desc",
			page_length=1,
		)

		if result:
			return result[0]


def set_total_marks(questions: list) -> int:
	marks = 0
	for question in questions:
		marks += question.get("marks")
	return marks


@frappe.whitelist()
def submit_quiz(quiz: str, results: str):
	results = results and json.loads(results)
	percentage = 0

	quiz_details = frappe.db.get_value(
		"Quiz",
		quiz,
		[
			"name",
			"total_marks",
			"passing_percentage",
			"lesson",
			"course",
			"enable_negative_marking",
			"marks_to_cut",
		],
		as_dict=1,
	)

	data = process_results(results, quiz_details)
	results = data["results"]
	score = data["score"]
	is_open_ended = data["is_open_ended"]

	score_out_of = quiz_details.total_marks
	percentage = (score / score_out_of) * 100 if score_out_of else 0
	submission = create_submission(quiz, results, score_out_of, quiz_details.passing_percentage)
	save_progress_after_quiz(quiz_details, percentage)

	return {
		"score": score,
		"score_out_of": score_out_of,
		"submission": submission.name,
		"pass": percentage >= quiz_details.passing_percentage,
		"percentage": percentage,
		"is_open_ended": is_open_ended,
	}


def process_results(results: list, quiz_details: dict):
	score = 0
	is_open_ended = False

	if not results:
		return {"results": [], "score": 0, "is_open_ended": False}

	for result in results:
		question_details = frappe.db.get_value(
			"Quiz Question",
			{"parent": quiz_details.name, "question": result["question_name"]},
			["question", "marks", "question_detail", "type"],
			as_dict=1,
		)
		result["question_name"] = question_details.question
		result["question"] = question_details.question_detail
		result["marks_out_of"] = question_details.marks

		if question_details.type != "Open Ended":
			marks_earned = calculate_weighted_marks(
				question_details.question, result["answer"], question_details.marks
			)
			result["answer"] = ", ".join(result["answer"])
			result["marks"] = marks_earned
			score += marks_earned
			result["is_correct"] = 1 if marks_earned > 0 else 0

		else:
			is_open_ended = True
			result["is_correct"] = 0
			result["answer"] = re.sub(
				r'<img[^>]*src\s*=\s*["\'](?=data:)(.*?)["\']', _save_file, result["answer"][0]
			)

	return {
		"results": results,
		"score": score,
		"is_open_ended": is_open_ended,
	}


def verify_answer(question: str, answer: list):
	question_details = get_question_details(question)
	correct = False

	if question_details.multiple:
		for num in range(1, 5):
			if question_details[f"option_{num}"] in answer:
				correct = question_details[f"is_correct_{num}"]
				if not correct:
					return False
			if question_details[f"is_correct_{num}"] and question_details[f"option_{num}"] not in answer:
				return False
		return True

	for num in range(1, 5):
		if question_details[f"option_{num}"] in answer:
			correct = question_details[f"is_correct_{num}"]
	return correct


def calculate_weighted_marks(question_name: str, selected_answers: list, max_marks) -> float:
	fields = ["weight_type"]
	for num in range(1, 5):
		fields.append(f"option_{cstr(num)}")
		fields.append(f"weight_{cstr(num)}")
	question_details = frappe.db.get_value("Question", question_name, fields, as_dict=1)
	weight_type = question_details.get("weight_type") or "Percentage"
	earned = 0.0
	for num in range(1, 5):
		option_text = question_details.get(f"option_{num}")
		weight = flt(question_details.get(f"weight_{num}") or 0)
		if option_text and option_text in selected_answers:
			if weight_type == "Points":
				earned += weight
			else:
				earned += (weight / 100.0) * flt(max_marks)
	return earned


def _save_file(match: re.Match) -> str:
	data = match.group(1).split("data:")[1]
	headers, content = data.split(",")
	mtype = headers.split(";", 1)[0]

	if isinstance(content, str):
		content = content.encode("utf-8")
	if b"," in content:
		content = content.split(b",")[1]

	try:
		content = safe_b64decode(content)
	except BinasciiError:
		frappe.flags.has_dataurl = True
		return f'<img src="#broken-image" alt="{get_corrupted_image_msg()}"'

	if "filename=" in headers:
		filename = headers.split("filename=")[-1]
		filename = safe_decode(filename).split(";", 1)[0]

	else:
		filename = get_random_filename(content_type=mtype)

	_file = frappe.get_doc(
		{
			"doctype": "File",
			"file_name": filename,
			"content": content,
			"decode": False,
			"is_private": False,
		}
	)
	_file.save(ignore_permissions=True)
	file_url = _file.unique_url
	frappe.flags.has_dataurl = True

	return f'<img src="{file_url}"'


def get_corrupted_image_msg():
	return _("Image: Corrupted Data Stream")


def create_submission(quiz: str, results: list, score_out_of: int, passing_percentage: float):
	submission = frappe.new_doc("Quiz Submission")
	# Score and percentage are calculated by the controller function
	submission.update(
		{
			"doctype": "Quiz Submission",
			"quiz": quiz,
			"result": results,
			"score": 0,
			"score_out_of": score_out_of,
			"member": frappe.session.user,
			"percentage": 0,
			"passing_percentage": passing_percentage,
		}
	)
	submission.save(ignore_permissions=True)
	return submission


def save_progress_after_quiz(quiz_details: dict, percentage: float):
	if not quiz_details.lesson or not quiz_details.course:
		return

	if quiz_details.passing_percentage and percentage < quiz_details.passing_percentage:
		return
	save_progress(quiz_details.lesson, quiz_details.course)


@frappe.whitelist()
def check_answer(question: str, question_type: str, answers: str):
	answers = answers and json.loads(answers)
	if question_type == "Choices":
		return check_choice_answers(question, answers)
	else:
		return check_input_answers(question, answers[0])


def get_question_details(question: str):
	fields = ["multiple"]
	for num in range(1, 5):
		fields.append(f"option_{cstr(num)}")

	question_details = frappe.db.get_value("Question", question, fields, as_dict=1)
	return question_details


def check_choice_answers(question: str, answers: list):
	is_correct = []
	question_details = get_question_details(question)

	for num in range(1, 5):
		if question_details[f"option_{num}"] in answers:
			is_correct.append(question_details[f"is_correct_{num}"])
		elif question_details[f"is_correct_{num}"]:
			is_correct.append(2)
		else:
			is_correct.append(0)

	return is_correct


def check_input_answers(question: str, answer: str):
	fields = []
	for num in range(1, 5):
		fields.append(f"possibility_{cstr(num)}")

	question_details = frappe.db.get_value("Question", question, fields, as_dict=1)
	for num in range(1, 5):
		current_possibility = question_details[f"possibility_{num}"]
		if current_possibility and fuzz.token_sort_ratio(current_possibility, answer) > 85:
			return 1

	return 0
