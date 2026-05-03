import type { VercelRequest, VercelResponse } from '@vercel/node';

export default function handler(req: VercelRequest, res: VercelResponse) {
  const hasKey = !!process.env.ODDSJAM_API_KEY;
  res.json({ status: 'ok', apiConnected: hasKey });
}
