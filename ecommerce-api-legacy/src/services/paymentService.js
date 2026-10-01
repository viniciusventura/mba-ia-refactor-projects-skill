// Gateway de pagamento simulado. A chave é injetada pela config e nunca vai para log.
const APPROVED_CARD_PREFIX = '4';
const VISIBLE_CARD_DIGITS = 4;

function maskCard(cardNumber) {
    return `**** ${cardNumber.slice(-VISIBLE_CARD_DIGITS)}`;
}

module.exports = ({ gatewayKey }) => ({
    isConfigured: Boolean(gatewayKey),

    // Retorna true se a cobrança foi aprovada.
    async charge({ cardNumber, amount }) {
        console.info(`[payment] cobrando ${amount} no cartão ${maskCard(cardNumber)}`);
        return cardNumber.startsWith(APPROVED_CARD_PREFIX);
    },
});
