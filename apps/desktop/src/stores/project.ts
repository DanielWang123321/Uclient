import { defineStore } from 'pinia'
import { ref } from 'vue'
import { migrate, newProject, type ProjectFile } from '../project/migrate'

export const useProjectStore = defineStore('project', () => {
  const project = ref<ProjectFile>(newProject())
  const path = ref<string | null>(null)

  function loadText(text: string, from: string | null = null) {
    project.value = migrate(JSON.parse(text))
    path.value = from
  }

  function toText() {
    return JSON.stringify(project.value, null, 2) + '\n'
  }

  return { project, path, loadText, toText }
})
