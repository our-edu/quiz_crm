import frappe

app_name = "quiz_crm"
app_title = "Quiz CRM"
app_publisher = "OurEdu"
app_description = "Quiz and Question management for CRM"
app_email = "dev@ouredu.com"
app_license = "MIT"


def get_quiz_path():
	path = "quiz"
	if frappe.conf and frappe.conf.get("quiz_path"):
		path = frappe.conf.get("quiz_path")
	return path.strip("/")


# Apps
# ------------------

add_to_apps_screen = [
	{
		"name": "quiz_crm",
		"logo": "/assets/quiz_crm/images/quiz_crm.png",
		"title": "Quiz CRM",
		"route": f"/{get_quiz_path()}",
	}
]

# Includes in <head>
# ------------------

web_include_css = "quiz_crm.bundle.css"

# Website Route Rules
# --------------------

website_route_rules = [
	{"from_route": f"/{get_quiz_path()}/<path:app_path>", "to_route": "_quiz_crm"},
	{"from_route": f"/{get_quiz_path()}", "to_route": "_quiz_crm"},
	{
		"from_route": "/courses/<course_name>/<certificate_id>",
		"to_route": "certificate",
	},
]

website_redirects = [
	{"source": "_quiz_crm", "target": f"/{get_quiz_path()}"},
]
