const { hashPassword } = require('../utils/password');

const TABLES = [
    `CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,
        name TEXT,
        email TEXT,
        pass TEXT,
        deleted INTEGER NOT NULL DEFAULT 0,
        deleted_at DATETIME
    )`,
    'CREATE TABLE IF NOT EXISTS courses (id INTEGER PRIMARY KEY, title TEXT, price REAL, active INTEGER)',
    'CREATE TABLE IF NOT EXISTS enrollments (id INTEGER PRIMARY KEY, user_id INTEGER, course_id INTEGER)',
    'CREATE TABLE IF NOT EXISTS payments (id INTEGER PRIMARY KEY, enrollment_id INTEGER, amount REAL, status TEXT)',
    'CREATE TABLE IF NOT EXISTS audit_logs (id INTEGER PRIMARY KEY, action TEXT, created_at DATETIME)',
];

// Migração idempotente: bancos em arquivo criados antes do soft delete ganham as colunas novas.
// Tabela e coluna são nomes internos fixos, nunca entrada do usuário.
async function ensureColumn(db, table, column, ddl) {
    const columns = await db.all(`PRAGMA table_info(${table})`);
    if (!columns.some((c) => c.name === column)) {
        await db.run(`ALTER TABLE ${table} ADD COLUMN ${ddl}`);
    }
}

async function seed(db) {
    const { total } = await db.get('SELECT COUNT(*) AS total FROM courses');
    if (total > 0) return;

    const seedPasswordHash = await hashPassword('123');
    await db.transaction(async (tx) => {
        await tx.run('INSERT INTO users (name, email, pass) VALUES (?, ?, ?)', ['Leonan', 'leonan@fullcycle.com.br', seedPasswordHash]);
        await tx.run("INSERT INTO courses (title, price, active) VALUES ('Clean Architecture', 997.00, 1), ('Docker', 497.00, 1)");
        await tx.run('INSERT INTO enrollments (user_id, course_id) VALUES (1, 1)');
        await tx.run("INSERT INTO payments (enrollment_id, amount, status) VALUES (1, 997.00, 'PAID')");
    });
}

async function initSchema(db) {
    for (const ddl of TABLES) {
        await db.run(ddl);
    }
    await ensureColumn(db, 'users', 'deleted', 'deleted INTEGER NOT NULL DEFAULT 0');
    await ensureColumn(db, 'users', 'deleted_at', 'deleted_at DATETIME');
    await seed(db);
}

module.exports = { initSchema };
