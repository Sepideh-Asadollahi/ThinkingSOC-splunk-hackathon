/** Default hackathon demo credentials (override via TSOC_DEMO_USER / TSOC_DEMO_PASSWORD). */
export const DEFAULT_DEMO_USERNAME = "admin"
export const DEFAULT_DEMO_PASSWORD = "123456@a"

export function getDemoUsername(): string {
  return process.env.TSOC_DEMO_USER || DEFAULT_DEMO_USERNAME
}

export function getDemoPassword(): string {
  return process.env.TSOC_DEMO_PASSWORD || DEFAULT_DEMO_PASSWORD
}

export function validateDemoCredentials(username: string, password: string): boolean {
  return username === getDemoUsername() && password === getDemoPassword()
}
