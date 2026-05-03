export default function handler(req: any, res: any) {
  res.json({ status: 'ok', apiConnected: !!process.env.ODDSJAM_API_KEY });
}
