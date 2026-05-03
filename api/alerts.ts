import type { VercelRequest, VercelResponse } from '@vercel/node';

export default async function handler(req: VercelRequest, res: VercelResponse) {
  // Move your Express alerts CRUD logic here
  // Use DATABASE_URL from process.env
  res.json({ ok: true });
}
