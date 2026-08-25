export type HealthResponse = {
  status: string;
  service: string;
  database: string;
};

export async function getHealth(): Promise<HealthResponse> {
  const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
  const response = await fetch(`${baseUrl}/api/health`, { cache: "no-store" });

  if (!response.ok) {
    throw new Error(`Backend health check failed: ${response.status}`);
  }

  return response.json();
}
