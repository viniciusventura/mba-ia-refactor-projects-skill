const reportModel = require('../models/reportModel');
const paymentModel = require('../models/paymentModel');

const UNKNOWN_STUDENT = 'Unknown';

// Agrupa as linhas do JOIN por curso, mantendo o formato original da resposta.
function buildFinancialReport(rows) {
    const byCourse = new Map();
    for (const row of rows) {
        if (!byCourse.has(row.course_id)) {
            byCourse.set(row.course_id, { course: row.title, revenue: 0, students: [] });
        }
        const courseData = byCourse.get(row.course_id);
        if (row.enrollment_id === null) continue;

        if (paymentModel.countsAsRevenue(row.status)) courseData.revenue += row.amount;
        courseData.students.push({
            student: row.student ?? UNKNOWN_STUDENT,
            paid: row.amount ?? 0,
        });
    }
    return [...byCourse.values()];
}

module.exports = ({ db }) => ({
    async financialReport(req, res) {
        const rows = await reportModel.financialRows(db);
        res.json(buildFinancialReport(rows));
    },
});
