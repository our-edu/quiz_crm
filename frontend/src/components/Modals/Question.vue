<template>
	<Dialog
		v-model="show"
		:options="{
			size: '3xl',
		}"
	>
		<template #body>
			<div class="p-5 space-y-5">
				<div class="text-lg font-semibold text-ink-gray-9 mb-5">
					{{ __(props.title) }}
				</div>
				<Switch
					v-if="!editMode"
					size="sm"
					:label="__('Choose an existing question')"
					:description="__('Select from questions you have already created')"
					v-model="chooseFromExisting"
					class="!p-0"
				/>
				<div v-if="!chooseFromExisting || editMode">
					<div>
						<label class="block text-xs text-ink-gray-5 mb-1">
							{{ __('Question') }}
						</label>
						<TextEditor
							:content="question.question"
							@change="(val) => (question.question = val)"
							:editable="true"
							:fixedMenu="true"
							editorClass="prose-sm max-w-none border-b border-x border-outline-gray-modals bg-surface-gray-2 rounded-b-md py-1 px-2 min-h-[7rem]"
						/>
					</div>
					<div class="grid grid-cols-2 gap-8 mt-4">
						<FormControl
							v-model="question.marks"
							:label="__('Marks')"
							type="number"
						/>
						<FormControl
							:label="__('Type')"
							v-model="question.type"
							type="select"
							:options="['Choices', 'User Input', 'Open Ended']"
							class="pb-2"
							:required="true"
						/>
						<Switch
							v-if="question.type === 'Choices'"
							size="sm"
							:label="__('Allow Multiple Selections')"
							:description="__('Let users select more than one option.')"
							v-model="question.multiple"
						/>
						<FormControl
							v-if="question.type === 'Choices'"
							:label="__('Weight Entry Mode')"
							v-model="question.weight_type"
							type="select"
							:options="[{ label: __('Percentage (0–100%)'), value: 'Percentage' }, { label: __('Points (up to question marks)'), value: 'Points' }]"
						/>
					</div>
					<div
						v-if="question.type == 'Choices'"
						class="text-base font-semibold text-ink-gray-9 mb-5 mt-10"
					>
						{{ __('Options') }}
					</div>
					<div
						v-else-if="question.type == 'User Input'"
						class="text-base font-semibold text-ink-gray-9 mb-5 mt-5"
					>
						{{ __('Possibilities') }}
					</div>
					<div v-if="question.type == 'Choices'" class="space-y-3">
						<div
							v-for="(option, i) in question.options"
							:key="i"
							class="grid grid-cols-12 gap-x-3 items-end border-b pb-3"
						>
							<FormControl
								class="col-span-5"
								:label="__('Option') + ' ' + (i + 1)"
								v-model="option.option"
								:required="i < 2"
							/>
							<FormControl
								class="col-span-4"
								:label="__('Explanation')"
								v-model="option.explanation"
							/>
							<FormControl
								class="col-span-2"
								:label="question.weight_type === 'Points' ? __('Points (max: ') + (question.marks || 1) + ')' : __('Weight (%)')"
								v-model="option.weight"
								type="number"
								:min="0"
								:max="question.weight_type === 'Points' ? (question.marks || 1) : 100"
							/>
							<Button
								class="col-span-1"
								variant="ghost"
								:disabled="question.options.length <= 2"
								:title="__('Remove option')"
								@click="question.options.splice(i, 1)"
							>
								<template #icon>
									<Trash2 class="w-4 h-4 stroke-1.5" />
								</template>
							</Button>
						</div>
						<Button @click="question.options.push(emptyOption())">
							<template #prefix>
								<Plus class="w-4 h-4 stroke-1.5" />
							</template>
							{{ __('Add Option') }}
						</Button>
					</div>
					<div
						v-else-if="question.type == 'User Input'"
						class="grid grid-cols-2 gap-x-8 gap-y-4 py-2"
					>
						<div v-for="n in 4">
							<FormControl
								:label="__('Possibility') + ' ' + n"
								v-model="question[`possibility_${n}`]"
								:required="n == 1 ? true : false"
							/>
						</div>
					</div>
				</div>
				<div v-else-if="chooseFromExisting" class="space-y-2">
					<Link
						v-model="existingQuestion.question"
						:label="__('Select a question')"
						doctype="Question"
					/>
					<FormControl
						v-model="existingQuestion.marks"
						:label="__('Marks')"
						type="number"
					/>
				</div>
				<div class="flex items-center justify-end space-x-2 mt-5">
					<Button variant="solid" @click="submitQuestion()">
						{{ __('Save') }}
					</Button>
				</div>
			</div>
		</template>
	</Dialog>
</template>
<script setup>
import {
	Dialog,
	FormControl,
	TextEditor,
	createResource,
	Switch,
	Button,
	toast,
} from 'frappe-ui'
import { watch, reactive, ref, inject } from 'vue'
import Link from '@/components/Controls/Link.vue'
import { Plus, Trash2 } from 'lucide-vue-next'
import { useOnboarding } from 'frappe-ui/frappe'

const show = defineModel()
const quiz = defineModel('quiz')
const chooseFromExisting = ref(false)
const editMode = ref(false)
const user = inject('$user')
const { updateOnboardingStep } = useOnboarding('learning') || { updateOnboardingStep: () => {} }

const existingQuestion = reactive({
	question: '',
	marks: 1,
})

const question = reactive({
	question: '',
	type: 'Choices',
	marks: 1,
	weight_type: 'Percentage',
	options: [],
})

// a choice question has any number of options (Question Option rows); two to start
const emptyOption = () => ({ option: '', explanation: '', weight: 0 })

// the rows to save: no blank options, numeric weights, no stale row metadata
const cleanOptions = () =>
	question.options
		.filter((o) => (o.option || '').trim())
		.map((o) => ({
			option: o.option,
			explanation: o.explanation || '',
			weight: parseFloat(o.weight) || 0,
		}))

const populateFields = () => {
	for (let n = 1; n <= 4; n++) question[`possibility_${n}`] = null
	question.options = [emptyOption(), emptyOption()]
	question.multiple = false
	question.weight_type = 'Percentage'
}

populateFields()

const props = defineProps({
	title: {
		type: String,
		default: __('Add new question'),
	},
	questionDetail: {
		type: [Object, null],
		required: true,
	},
})

const questionData = createResource({
	url: 'frappe.client.get',
	makeParams() {
		return {
			doctype: 'Question',
			name: props.questionDetail.question,
		}
	},
	auto: false,
	onSuccess(data) {
		editMode.value = true
		Object.keys(data).forEach((key) => {
			if (Object.hasOwn(question, key)) question[key] = data[key]
		})
		question.options = (data.options || []).map((o) => ({
			option: o.option,
			explanation: o.explanation || '',
			weight: o.weight || 0,
		}))
		while (question.options.length < 2) question.options.push(emptyOption())
		question.multiple = data.multiple ? true : false
		question.weight_type = data.weight_type || 'Percentage'
		question.marks = props.questionDetail.marks
	},
})

watch(show, () => {
	if (show.value) {
		editMode.value = false
		if (props.questionDetail.question) questionData.fetch()
		else {
			question.question = ''
			question.marks = 1
			question.type = 'Choices'
			existingQuestion.question = ''
			existingQuestion.marks = 1
			chooseFromExisting.value = false
			populateFields()
		}

		if (props.questionDetail.marks) question.marks = props.questionDetail.marks
	}
})

const questionRow = createResource({
	url: 'frappe.client.insert',
	makeParams(values) {
		return {
			doc: {
				doctype: 'Quiz Question',
				parent: quiz.value.doc.name,
				parentfield: 'questions',
				parenttype: 'Quiz',
				...values,
			},
		}
	},
})

const questionCreation = createResource({
	url: 'frappe.client.insert',
	makeParams(values) {
		const { marks, ...questionDoc } = question
		return {
			doc: {
				doctype: 'Question',
				...questionDoc,
				options: questionDoc.type === 'Choices' ? cleanOptions() : [],
				multiple: questionDoc.multiple ? 1 : 0,
			},
		}
	},
})

const submitQuestion = () => {
	if (question.type === 'Choices') {
		const options = cleanOptions()
		if (options.length < 2) {
			toast.warning(__('Add at least two options.'))
			return
		}
		const maxW = question.weight_type === 'Points' ? parseFloat(question.marks || 1) : 100
		for (const [i, option] of options.entries()) {
			if (option.weight < 0 || option.weight > maxW) {
				const unit = question.weight_type === 'Points' ? `points (max: ${maxW})` : '% (max: 100)'
				toast.warning(`Weight for Option ${i + 1} must be between 0 and ${maxW} ${unit}.`)
				return
			}
		}
	}
	if (props.questionDetail?.question) updateQuestion()
	else addQuestion()
}

const addQuestion = () => {
	if (chooseFromExisting.value) {
		addQuestionRow({
			question: existingQuestion.question,
			marks: existingQuestion.marks,
		})
	} else {
		questionCreation.submit(
			{},
			{
				onSuccess(data) {
					addQuestionRow({
						question: data.name,
						marks: question.marks,
					})
				},
				onError(err) {
					toast.error(err.messages?.[0] || err)
				},
			}
		)
	}
}

const addQuestionRow = (question) => {
	questionRow.submit(
		{
			...question,
		},
		{
			onSuccess() {
				if (user.data?.is_system_manager)
					updateOnboardingStep('create_first_quiz')

				show.value = false
				toast.success(__('Question added successfully'))
				quiz.value.reload()
				show.value = false
			},
			onError(err) {
				toast.error(err.messages?.[0] || err)
				show.value = false
			},
		}
	)
}

const questionUpdate = createResource({
	url: 'frappe.client.set_value',
	auto: false,
	makeParams(values) {
		const { marks, ...questionDoc } = question
		return {
			doctype: 'Question',
			name: questionData.data?.name,
			fieldname: {
				...questionDoc,
				options: questionDoc.type === 'Choices' ? cleanOptions() : [],
				multiple: questionDoc.multiple ? 1 : 0,
			},
		}
	},
})

const marksUpdate = createResource({
	url: 'frappe.client.set_value',
	auto: false,
	makeParams(values) {
		return {
			doctype: 'Quiz Question',
			name: props.questionDetail.name,
			fieldname: {
				marks: question.marks,
			},
		}
	},
})

const updateQuestion = () => {
	questionUpdate.submit(
		{},
		{
			onSuccess() {
				marksUpdate.submit(
					{},
					{
						onSuccess() {
							show.value = false
							toast.success(__('Question updated successfully'))
							quiz.value.reload()
						},
					}
				)
			},
			onError(err) {
				toast.error(err.messages?.[0] || err)
			},
		}
	)
}
</script>
<style>
input[type='radio']:checked {
	background-color: theme('colors.gray.900') !important;
	border-color: theme('colors.gray.900') !important;
	--tw-ring-color: theme('colors.gray.900') !important;
}
</style>
