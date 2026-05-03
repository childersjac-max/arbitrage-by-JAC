export default async function handler(req: any, res: any) {
  const apiKey = process.env.ODDSJAM_API_KEY;
  if (!apiKey) return res.status(401).json({ error: 'No API key' });
  const params = new URLSearchParams(req.query);
  const response = await fetch(`https://api.oddsjam.com/api/v2/game-odds?key=${apiKey}&${params}`);
  const data = await response.json();
  res.json(data);
}
