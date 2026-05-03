export default function handler(req: any, res: any) {
  res.json({ apiKey: process.env.ODDSJAM_API_KEY ?? '' });
}
