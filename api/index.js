// Vercel Functions 진입점. server.js가 만든 Express 앱을 그대로 가져다 씁니다.
// server.js는 require.main === module일 때만 app.listen()을 호출하므로,
// 여기서는 그냥 요청 핸들러(app)만 재사용됩니다.
module.exports = require("../server.js");
