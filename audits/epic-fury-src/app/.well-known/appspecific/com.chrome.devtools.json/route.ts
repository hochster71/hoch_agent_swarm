/**
 * Chrome 121+ automatically requests this URL from any localhost origin.
 * Return an empty JSON object so it doesn't 404 or trigger CSP violations.
 */
export async function GET() {
  return Response.json({})
}
