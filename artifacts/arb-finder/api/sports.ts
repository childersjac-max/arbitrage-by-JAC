export default async function handler(req: any, res: any) {
  const apiKey = process.env.ODDSJAM_API_KEY;
  if (!apiKey) return res.status(401).json({ error: 'No API key' });
  const response = await fetch(`https://api.oddsjam.com/api/v2/sports?key=${apiKey}`);
  const data = await response.json();
  res.json(data);
}
