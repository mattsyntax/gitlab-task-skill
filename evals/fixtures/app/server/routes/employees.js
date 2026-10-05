const express = require("express");
const multer = require("multer");
const db = require("../db");

const router = express.Router();
const upload = multer({ dest: "uploads/" });

router.get("/employees/:id", async (req, res) => {
  res.json(await db.one("SELECT * FROM employees WHERE id = $1", [req.params.id]));
});

router.post("/employees/:id/photo", upload.single("photo"), async (req, res) => {
  await db.query("UPDATE employees SET photo = $1 WHERE id = $2", [req.file.path, req.params.id]);
  res.status(204).end();
});

module.exports = router;
