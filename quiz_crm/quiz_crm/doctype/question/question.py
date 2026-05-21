# Copyright (c) 2023, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt
from frappe.model.document import Document

from quiz_crm.quiz_crm.utils import has_course_instructor_role, has_moderator_role


class Question(Document):
	def validate(self):
		validate_correct_answers(self)
		update_question_title(self)


def validate_correct_answers(question):
	if question.type == "Choices":
		validate_duplicate_options(question)
		validate_minimum_options(question)
		validate_weights(question)
	elif question.type == "User Input":
		validate_possible_answer(question)


def validate_duplicate_options(question):
	options = []

	for num in range(1, 5):
		if question.get(f"option_{num}"):
			options.append(question.get(f"option_{num}"))

	if len(set(options)) != len(options):
		frappe.throw(_("Duplicate options found for this question."))


def validate_weights(question):
	weight_type = question.get("weight_type") or "Percentage"
	marks = flt(question.get("marks") or 0)

	for n in range(1, 5):
		w = flt(question.get(f"weight_{n}") or 0)
		if w < 0:
			frappe.throw(_("Weight for Option {0} cannot be negative.").format(n))
		if weight_type == "Percentage" and w > 100:
			frappe.throw(_("Weight for Option {0} must be between 0 and 100%.").format(n))


def validate_minimum_options(question):
	if question.type == "Choices" and (not question.option_1 or not question.option_2):
		frappe.throw(_("Minimum two options are required for multiple choice questions."))


def validate_possible_answer(question):
	possible_answers = []
	possible_answers_fields = [
		"possibility_1",
		"possibility_2",
		"possibility_3",
		"possibility_4",
	]

	for field in possible_answers_fields:
		if question.get(field):
			possible_answers.append(field)

	if not len(possible_answers):
		frappe.throw(
			_("Add at least one possible answer for this question: {0}").format(
				frappe.bold(question.question)
			)
		)


def update_question_title(question):
	if not question.is_new():
		question_rows = frappe.get_all("Quiz Question", {"question": question.name}, pluck="name")

		for row in question_rows:
			frappe.db.set_value("Quiz Question", row, "question_detail", question.question)



