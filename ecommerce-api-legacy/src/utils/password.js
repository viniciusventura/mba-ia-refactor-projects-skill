const crypto = require('crypto');
const { promisify } = require('util');

const scrypt = promisify(crypto.scrypt);

const SALT_BYTES = 16;
const KEY_LENGTH = 64;
const RANDOM_PASSWORD_BYTES = 24;

// Formato gravado: "<salt hex>:<hash hex>"
async function hashPassword(password) {
    const salt = crypto.randomBytes(SALT_BYTES).toString('hex');
    const derived = await scrypt(password, salt, KEY_LENGTH);
    return `${salt}:${derived.toString('hex')}`;
}

// Usada quando o checkout cria um usuário sem senha: ninguém conhece o valor, só o hash é gravado.
function generateRandomPassword() {
    return crypto.randomBytes(RANDOM_PASSWORD_BYTES).toString('base64url');
}

module.exports = { hashPassword, generateRandomPassword };
