const crypto = require('crypto');
const { AppError } = require('./errorHandler');

function safeEqual(a, b) {
    const x = Buffer.from(String(a));
    const y = Buffer.from(String(b));
    return x.length === y.length && crypto.timingSafeEqual(x, y);
}

// Exige "Authorization: Bearer <ADMIN_TOKEN>". Sem token configurado, a rota fica fechada.
function createRequireAdmin(adminToken) {
    return function requireAdmin(req, res, next) {
        const header = req.get('Authorization') || '';
        const token = header.startsWith('Bearer ') ? header.slice('Bearer '.length).trim() : '';
        if (!adminToken || !token || !safeEqual(token, adminToken)) {
            return next(new AppError('Não autorizado', 401));
        }
        next();
    };
}

module.exports = { createRequireAdmin };
