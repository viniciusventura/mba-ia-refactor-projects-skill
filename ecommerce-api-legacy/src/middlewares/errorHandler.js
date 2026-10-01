class AppError extends Error {
    constructor(message, status = 400) {
        super(message);
        this.status = status;
    }
}

// Express 4 não captura rejeições de handlers async.
const asyncHandler = (fn) => (req, res, next) => Promise.resolve(fn(req, res, next)).catch(next);

// As respostas de erro do projeto são texto puro; o formato é mantido.
function errorHandler(err, req, res, next) {
    if (res.headersSent) return next(err);
    if (err instanceof AppError) return res.status(err.status).send(err.message);

    const status = err.status || err.statusCode;
    if (status && status < 500) return res.status(status).send(status === 400 ? 'Bad Request' : err.message);

    console.error('[error]', err);
    res.status(500).send('Erro interno');
}

module.exports = { AppError, asyncHandler, errorHandler };
