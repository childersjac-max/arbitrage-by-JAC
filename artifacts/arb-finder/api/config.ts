import type { VercelRequest, VercelResponse } from '@vercel/node';

export default function handler(req: VercelRequest, res: VercelResponse) {
  res.json({ apiKey: process.env.ODDSJAM_API_KEY ?? '' });
}
