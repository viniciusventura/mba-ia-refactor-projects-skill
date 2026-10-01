const PAYMENT_STATUS = Object.freeze({ PAID: 'PAID', DENIED: 'DENIED' });

async function create(db, { enrollmentId, amount, status }) {
    const { lastID } = await db.run(
        'INSERT INTO payments (enrollment_id, amount, status) VALUES (?, ?, ?)',
        [enrollmentId, amount, status],
    );
    return lastID;
}

// Regra de domínio: só pagamentos confirmados contam como faturamento.
function countsAsRevenue(status) {
    return status === PAYMENT_STATUS.PAID;
}

module.exports = { PAYMENT_STATUS, create, countsAsRevenue };
