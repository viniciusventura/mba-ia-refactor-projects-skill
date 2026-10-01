const courseModel = require('../models/courseModel');
const userModel = require('../models/userModel');
const enrollmentModel = require('../models/enrollmentModel');
const paymentModel = require('../models/paymentModel');
const auditLogModel = require('../models/auditLogModel');
const { AppError } = require('../middlewares/errorHandler');
const { hashPassword, generateRandomPassword } = require('../utils/password');

const COURSE_ID_PATTERN = /^\d+$/;

// Contrato mantido: usr, eml, pwd (opcional), c_id, card.
function parseCheckoutInput(body) {
    const { usr: name, eml: email, pwd: password, c_id: courseId, card: cardNumber } = body || {};
    if (!name || !email || !courseId || !cardNumber) throw new AppError('Bad Request', 400);

    const validTypes = typeof name === 'string'
        && typeof email === 'string'
        && typeof cardNumber === 'string'
        && (password === undefined || password === null || typeof password === 'string')
        && COURSE_ID_PATTERN.test(String(courseId));
    if (!validTypes) throw new AppError('Bad Request', 400);

    return { name, email, password: password || null, courseId: Number(courseId), cardNumber };
}

module.exports = ({ db, paymentService }) => ({
    async checkout(req, res) {
        const input = parseCheckoutInput(req.body);

        const course = await courseModel.findActiveById(db, input.courseId);
        if (!course) throw new AppError('Curso não encontrado', 404);

        const approved = await paymentService.charge({ cardNumber: input.cardNumber, amount: course.price });
        if (!approved) throw new AppError('Pagamento recusado', 400);

        // Usuário, matrícula, pagamento e auditoria: tudo ou nada.
        const enrollmentId = await db.transaction(async (tx) => {
            const user = await userModel.findActiveByEmail(tx, input.email);
            const userId = user
                ? user.id
                : await userModel.create(tx, {
                    name: input.name,
                    email: input.email,
                    passwordHash: await hashPassword(input.password || generateRandomPassword()),
                });

            const newEnrollmentId = await enrollmentModel.create(tx, { userId, courseId: input.courseId });
            await paymentModel.create(tx, {
                enrollmentId: newEnrollmentId,
                amount: course.price,
                status: paymentModel.PAYMENT_STATUS.PAID,
            });
            await auditLogModel.create(tx, `Checkout curso ${input.courseId} por ${userId}`);
            return newEnrollmentId;
        });

        res.status(200).json({ msg: 'Sucesso', enrollment_id: enrollmentId });
    },
});
