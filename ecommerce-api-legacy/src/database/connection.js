const sqlite3 = require('sqlite3');

// Envolve a conexão sqlite3 (API de callbacks) em helpers baseados em Promise.
function wrap(rawDb) {
    // As transações da mesma conexão são enfileiradas: o SQLite não aceita BEGIN aninhado.
    let transactionQueue = Promise.resolve();

    const db = {
        get: (sql, params = []) => new Promise((resolve, reject) => {
            rawDb.get(sql, params, (err, row) => (err ? reject(err) : resolve(row)));
        }),
        all: (sql, params = []) => new Promise((resolve, reject) => {
            rawDb.all(sql, params, (err, rows) => (err ? reject(err) : resolve(rows)));
        }),
        run: (sql, params = []) => new Promise((resolve, reject) => {
            rawDb.run(sql, params, function onRun(err) {
                if (err) return reject(err);
                resolve({ lastID: this.lastID, changes: this.changes });
            });
        }),
        transaction(work) {
            const result = transactionQueue.then(async () => {
                await db.run('BEGIN');
                try {
                    const value = await work(db);
                    await db.run('COMMIT');
                    return value;
                } catch (err) {
                    await db.run('ROLLBACK');
                    throw err;
                }
            });
            transactionQueue = result.catch(() => {});
            return result;
        },
        close: () => new Promise((resolve, reject) => {
            rawDb.close((err) => (err ? reject(err) : resolve()));
        }),
    };
    return db;
}

function createConnection(filename) {
    return new Promise((resolve, reject) => {
        const rawDb = new sqlite3.Database(filename, (err) => (err ? reject(err) : resolve(wrap(rawDb))));
    });
}

module.exports = { createConnection };
