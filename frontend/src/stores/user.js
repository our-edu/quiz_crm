import { defineStore } from 'pinia'
import { createResource } from 'frappe-ui'

export const usersStore = defineStore('quiz-users', () => {
	let userResource = createResource({
		url: 'quiz_crm.quiz_crm.api.get_user_info',
		onError(error) {
			if (error && error.exc_type === 'AuthenticationError') {
				window.location.href = '/login'
			}
		},
	})

	const allUsers = createResource({
		url: 'quiz_crm.quiz_crm.api.get_all_users',
		cache: ['allUsers'],
	})

	return {
		userResource,
		allUsers,
	}
})
