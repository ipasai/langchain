import fs from 'fs'
import path from 'path'
import { randomUUID } from 'crypto'

function getStorePath() {
  return path.resolve(process.cwd(), '..', 'data', 'learning_jobs.json')
}

function readJobs() {
  try {
    const jobs = JSON.parse(fs.readFileSync(getStorePath(), 'utf8'))
    return jobs && typeof jobs === 'object' ? jobs : {}
  } catch (error) {
    return {}
  }
}

function writeJobs(jobs) {
  const filePath = getStorePath()
  fs.mkdirSync(path.dirname(filePath), { recursive: true })
  fs.writeFileSync(filePath, JSON.stringify(jobs, null, 2), 'utf8')
}

export function saveLearningJob(workflow) {
  const jobId = randomUUID()
  const jobs = readJobs()
  jobs[jobId] = { created_at: new Date().toISOString(), workflow }
  const entries = Object.entries(jobs).sort((a, b) => b[1].created_at.localeCompare(a[1].created_at)).slice(0, 20)
  writeJobs(Object.fromEntries(entries))
  return jobId
}

export function getValidatedTeachingBlock(jobId, blockId) {
  const job = readJobs()[jobId]?.workflow
  if (!job) throw Object.assign(new Error('教學稿工作階段不存在或已過期，請重新產生。'), { status: 404 })
  if (!job.tts_ready || job.validation?.status !== 'pass') {
    throw Object.assign(new Error('內容完整性尚未通過，禁止進行語音合成。'), { status: 409 })
  }
  for (const section of job.sections || []) {
    const block = (section.teaching_blocks || []).find((item) => item.block_id === blockId)
    if (block) return block
  }
  throw Object.assign(new Error('找不到指定的教學區塊。'), { status: 404 })
}
