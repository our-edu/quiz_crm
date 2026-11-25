import frappe
from frappe.utils import flt

LEGACY_OPTION_COUNT = 4


def execute():
	"""Questions used to have four fixed option fields (option_N, weight_N,
	explanation_N). Copy them into the new "options" table (Question Option rows).

	The old columns are no longer doctype fields but still exist in the database
	(Frappe doesn't drop columns), so they're read with SQL. Questions that already
	have option rows are left alone, so the patch is safe to run again."""
	columns = set(frappe.db.get_table_columns("Question"))
	legacy = [n for n in range(1, LEGACY_OPTION_COUNT + 1) if f"option_{n}" in columns]
	if not legacy:
		return

	def column(name):
		return f"`{name}`" if name in columns else "NULL"

	select = ", ".join(
		f"{column(f'{field}_{n}')} as {field}_{n}" for n in legacy for field in ("option", "weight", "explanation")
	)
	already_migrated = set(
		frappe.get_all("Question Option", filters={"parenttype": "Question"}, pluck="parent", distinct=True)
	)

	for row in frappe.db.sql(f"select name, {select} from `tabQuestion`", as_dict=True):
		if row.name in already_migrated:
			continue
		for idx, n in enumerate((n for n in legacy if row.get(f"option_{n}")), start=1):
			frappe.get_doc(
				{
					"doctype": "Question Option",
					"parent": row.name,
					"parenttype": "Question",
					"parentfield": "options",
					"idx": idx,
					"option": row.get(f"option_{n}"),
					"weight": flt(row.get(f"weight_{n}")),
					"explanation": row.get(f"explanation_{n}"),
				}
			).db_insert()
