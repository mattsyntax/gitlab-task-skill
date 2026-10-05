const express = require("express");
const db = require("../db");

const router = express.Router();

// GET /api/leaderboard - closed vacancies per recruiter, all time
router.get("/", async (req, res) => {
  const rows = await db.query(
    `SELECT r.id, r.name, COUNT(v.id) AS closed
       FROM recruiters r
       LEFT JOIN vacancies v ON v.recruiter_id = r.id AND v.status = 'closed'
      GROUP BY r.id
      ORDER BY closed DESC`
  );
  res.json(rows);
});

module.exports = router;
