module.exports = async function handler(req, res) {
  try {
    const r = await fetch(
      "https://raw.githubusercontent.com/childersjac-max/Line-Tracker-Model/main/pipeline_output/patterns.json?t=" + Date.now()
    );
    if (!r.ok) throw new Error("HTTP " + r.status);
    const data = await r.json();
    res.json(data);
  } catch (e) {
    res.status(500).json({ error: "fetch_failed", message: e.message });
  }
};
