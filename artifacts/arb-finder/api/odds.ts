import type { VercelRequest, VercelResponse } from '@vercel/node';

export default async function handler(req: VercelRequest, res: VercelResponse) {
  const apiKey = process.env.ODDSJAM_API_KEY;
  if (!apiKey) return res.status(401).json({ error: 'No API key configured' });

  const params = new URLSearchParams(req.query as Record<string, string>);
  const response = await fetch(`https://api.oddsjam.com/api/v2/game-odds?key=${apiKey}&${params}`);
  const data = await response.json();
  res.json(data);
}
