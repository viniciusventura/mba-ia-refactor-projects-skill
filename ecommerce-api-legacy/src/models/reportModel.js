// Leitura histórica: NÃO filtra usuários removidos, para o relatório manter o nome do aluno.
// Uma única query no lugar de 1 + C + 2E (N+1).
function financialRows(db) {
    return db.all(`
        SELECT c.id AS course_id, c.title, e.id AS enrollment_id,
               u.name AS student, p.amount, p.status
        FROM courses c
        LEFT JOIN enrollments e ON e.course_id = c.id
        LEFT JOIN users u       ON u.id = e.user_id
        LEFT JOIN payments p    ON p.id = (
            SELECT MIN(p2.id) FROM payments p2 WHERE p2.enrollment_id = e.id
        )
        ORDER BY c.id, e.id`);
}

module.exports = { financialRows };
