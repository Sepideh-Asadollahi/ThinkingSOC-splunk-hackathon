/** Where bare host / IP visits should land (no path in the URL bar). */
export function getHomeRedirectPath(hasSession: boolean): "/login" | "/dashboard" {
  return hasSession ? "/dashboard" : "/login"
}
