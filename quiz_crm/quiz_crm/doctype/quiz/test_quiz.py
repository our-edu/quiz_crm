# Copyright (c) 2021, FOSS United and Contributors
# See license.txt

import unittest

import frappe

from quiz_crm.quiz_crm.doctype.quiz.quiz import (
	calculate_weighted_marks,
	check_choice_answers,
	verify_answer,
)

TEST_QUESTION_PREFIX = "Test Quiz Question"


def make_question(options, multiple=0, weight_type="Percentage", save=True):
	"""A Choices question with the given [(option, weight), ...] rows."""
	question = frappe.new_doc("Question")
	question.question = f"{TEST_QUESTION_PREFIX} {frappe.generate_hash(length=6)}"
	question.type = "Choices"
	question.multiple = multiple
	question.weight_type = weight_type
	for option, weight in options:
		question.append("options", {"option": option, "weight": weight})
	if save:
		question.insert(ignore_permissions=True)
	return question


class TestQuiz(unittest.TestCase):
	@classmethod
	def setUpClass(cls) -> None:
		frappe.get_doc({"doctype": "Quiz", "title": "Test Quiz", "passing_percentage": 90}).save()

	def test_any_number_of_options(self):
		options = [(f"Option {n}", n * 10) for n in range(1, 8)]
		question = make_question(options)
		self.assertEqual([row.option for row in question.options], [o for o, _ in options])
		# the 7th option is graded like any other: 70% of 10 marks
		self.assertEqual(calculate_weighted_marks(question.name, ["Option 7"], 10), 7)

	def test_minimum_two_options(self):
		question = make_question([("Only option", 100)], save=False)
		self.assertRaises(frappe.ValidationError, question.insert)

	def test_duplicate_options(self):
		question = make_question([("Same", 100), ("Same", 0)], save=False)
		self.assertRaises(frappe.ValidationError, question.insert)

	def test_percentage_weight_limit(self):
		question = make_question([("A", 120), ("B", 0)], save=False)
		self.assertRaises(frappe.ValidationError, question.insert)

	def test_points_and_cap(self):
		question = make_question([("A", 3), ("B", 4), ("C", 0)], multiple=1, weight_type="Points")
		self.assertEqual(calculate_weighted_marks(question.name, ["A"], 5), 3)
		# A + B = 7 points, capped at the question's 5 marks
		self.assertEqual(calculate_weighted_marks(question.name, ["A", "B"], 5), 5)

	def test_check_and_verify_answers(self):
		question = make_question([("A", 100), ("B", 0), ("C", 50), ("D", 0), ("E", 0)], multiple=1)
		# per option: selected+correct=1, selected+wrong=0, missed correct=2, else 0
		self.assertEqual(check_choice_answers(question.name, ["A", "B"]), [1, 0, 2, 0, 0])
		self.assertTrue(verify_answer(question.name, ["A", "C"]))
		self.assertFalse(verify_answer(question.name, ["A"]))

	def test_legacy_option_fields_are_converted(self):
		"""Old course exports carry option_N / weight_N fields."""
		question = frappe.new_doc("Question")
		question.update(
			{
				"question": f"{TEST_QUESTION_PREFIX} legacy",
				"type": "Choices",
				"option_1": "Yes",
				"weight_1": 100,
				"option_2": "No",
				"weight_2": 0,
			}
		)
		question.insert(ignore_permissions=True)
		self.assertEqual([(r.option, r.weight) for r in question.options], [("Yes", 100), ("No", 0)])

	def test_with_no_possible_answers(self):
		question = frappe.new_doc("Question")
		question.question = f"{TEST_QUESTION_PREFIX} input"
		question.type = "User Input"
		self.assertRaises(frappe.ValidationError, question.save)

	@classmethod
	def tearDownClass(cls) -> None:
		frappe.db.delete("Quiz", "test-quiz")
		# only the questions created by these tests (not every question on the site)
		for name in frappe.get_all(
			"Question", filters={"question": ("like", f"%{TEST_QUESTION_PREFIX}%")}, pluck="name"
		):
			frappe.delete_doc("Question", name, force=True, ignore_permissions=True)
