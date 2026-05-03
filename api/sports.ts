import type { VercelRequest, VercelResponse } from '@vercel/node';

export default async function handler(req: VercelRequest, res: VercelResponse) {
  const apiKey = process.env.ODDSJAM_API_KEY;
  if (!apiKey) return res.status(401).json({ error: 'No API key configured' });

  const response = await fetch(`https://api.oddsjam.com/api/v2/sports?key=${apiKey}`);
  const data = await response.json();
  res.json(data);
}
