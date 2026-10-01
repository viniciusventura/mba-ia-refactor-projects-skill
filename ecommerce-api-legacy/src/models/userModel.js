// Leituras de negócio ignoram usuários removidos (soft delete).
function findActiveByEmail(db, email) {
    return db.get('SELECT id FROM users WHERE email = ? AND deleted = 0', [email]);
}

async function create(db, { name, email, passwordHash }) {
    const { lastID } = await db.run('INSERT INTO users (name, email, pass) VALUES (?, ?, ?)', [name, email, passwordHash]);
    return lastID;
}

// Matrículas, pagamentos e auditoria do usuário são histórico e ficam intactos.
async function softDelete(db, id) {
    const { changes } = await db.run(
        "UPDATE users SET deleted = 1, deleted_at = datetime('now') WHERE id = ? AND deleted = 0",
        [id],
    );
    return changes > 0;
}

module.exports = { findActiveByEmail, create, softDelete };
