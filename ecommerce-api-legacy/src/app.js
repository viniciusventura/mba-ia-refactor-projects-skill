// Composition root: cria as dependências, injeta nas camadas e sobe o servidor.
const express = require('express');
const config = require('./config');
const { createConnection } = require('./database/connection');
const { initSchema } = require('./database/schema');
const createPaymentService = require('./services/paymentService');
const createCheckoutController = require('./controllers/checkoutController');
const createReportController = require('./controllers/reportController');
const createUserController = require('./controllers/userController');
const buildRoutes = require('./routes');
const { createRequireAdmin } = require('./middlewares/auth');
const { errorHandler } = require('./middlewares/errorHandler');

async function createApp() {
    const db = await createConnection(config.databaseFile);
    await initSchema(db);

    const paymentService = createPaymentService({ gatewayKey: config.paymentGatewayKey });

    const app = express();
    app.use(express.json());
    app.use(buildRoutes({
        checkoutController: createCheckoutController({ db, paymentService }),
        reportController: createReportController({ db }),
        userController: createUserController({ db }),
        requireAdmin: createRequireAdmin(config.adminToken),
    }));
    app.use(errorHandler);

    return { app, db, paymentService };
}

async function main() {
    const { app, paymentService } = await createApp();
    if (!config.adminToken) console.warn('[config] ADMIN_TOKEN não definido: rotas administrativas responderão 401.');
    if (!paymentService.isConfigured) console.warn('[config] PAYMENT_GATEWAY_KEY não definido.');
    app.listen(config.port, () => {
        console.info(`LMS API rodando na porta ${config.port}`);
    });
}

if (require.main === module) {
    main().catch((err) => {
        console.error('[boot] falha ao iniciar', err);
        process.exit(1);
    });
}

module.exports = { createApp };
