const { faker } = require("@faker-js/faker");
const db = require("./db");

async function main() {
  for (let i = 0; i < 20; i++) {
    await db.query("INSERT INTO recruiters (name) VALUES ($1)", [faker.person.fullName()]);
  }
}

main();
