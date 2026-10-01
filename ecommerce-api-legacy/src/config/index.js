// Única fonte de configuração: tudo vem do ambiente, sem segredos no código.
module.exports = {
    port: Number(process.env.PORT) || 3000,
    databaseFile: process.env.DATABASE_FILE || ':memory:',
    paymentGatewayKey: process.env.PAYMENT_GATEWAY_KEY,
    adminToken: process.env.ADMIN_TOKEN,
};
