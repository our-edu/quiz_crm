# Copyright (c) 2023, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

from quiz_crm.quiz_crm.utils import has_course_instructor_role, has_moderator_role


class Assignment(Document):
	pass
