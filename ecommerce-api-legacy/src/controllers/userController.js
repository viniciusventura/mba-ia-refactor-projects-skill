const userModel = require('../models/userModel');

module.exports = ({ db }) => ({
    // Soft delete. Id inexistente ou já removido mantém o 200 do contrato original.
    async deleteUser(req, res) {
        await userModel.softDelete(db, req.params.id);
        res.send('Usuário removido.');
    },
});
