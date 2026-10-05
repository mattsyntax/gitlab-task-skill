const express = require("express");

const app = express();
app.use(express.json());
app.use("/api/leaderboard", require("./routes/leaderboard"));
app.use("/api", require("./routes/employees"));

app.listen(process.env.PORT || 3000);
