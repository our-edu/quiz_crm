import { defineStore } from 'pinia'
import { ref } from 'vue'
import { createResource } from 'frappe-ui'

export const useSettings = defineStore('settings', () => {
	const isSettingsOpen = ref(false)
	const isCommandPaletteOpen = ref(false)
	const activeTab = ref(null)

	const settings = createResource({
		url: 'quiz_crm.quiz_crm.api.get_settings',
		auto: true,
		cache: 'LMS Settings',
	})

	const sidebarSettings = createResource({
		url: 'quiz_crm.quiz_crm.api.get_sidebar_settings',
		cache: 'Sidebar Settings',
		auto: false,
	})

	const programs = createResource({
		url: 'quiz_crm.quiz_crm.utils.get_programs',
		auto: false,
	})

	return {
		activeTab,
		isSettingsOpen,
		isCommandPaletteOpen,
		programs,
		settings,
		sidebarSettings,
	}
})
