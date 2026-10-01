const { Router } = require('express');
const { asyncHandler } = require('../middlewares/errorHandler');

// View: só liga URL + método ao controller (e à proteção da rota).
module.exports = ({ checkoutController, reportController, userController, requireAdmin }) => {
    const router = Router();

    router.post('/api/checkout', asyncHandler(checkoutController.checkout));
    router.get('/api/admin/financial-report', requireAdmin, asyncHandler(reportController.financialReport));
    router.delete('/api/users/:id', requireAdmin, asyncHandler(userController.deleteUser));

    return router;
};
