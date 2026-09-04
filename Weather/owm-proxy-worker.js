// Cloudflare Worker: OpenWeatherMap 요청을 대신 보내주는 프록시.
// API 키는 이 코드가 아니라 Cloudflare 대시보드의 "환경 변수(Secret)"에만 저장되므로
// 브라우저에도, git 저장소에도 절대 노출되지 않습니다.
//
// 배포 방법
// 1) https://dash.cloudflare.com 무료 계정으로 로그인
// 2) 왼쪽 메뉴 Workers & Pages -> Create -> Create Worker
// 3) 에디터에 이 파일 내용을 그대로 붙여넣고 Deploy
// 4) Worker 관리 화면 -> Settings -> Variables -> "Add variable"
//    - Name: OPENWEATHER_API_KEY
//    - Value: 실제 발급받은 키
//    - "Encrypt" 체크 (Secret으로 저장)
// 5) 아래 ALLOWED_ORIGIN을 실제 배포될 사이트 주소로 바꾸고 다시 Deploy
// 6) 화면 상단에 뜨는 워커 주소(https://xxx.workers.dev)를
//    weatherhomepage.html의 WORKER_BASE에 붙여넣기

const ALLOWED_ORIGIN = 'https://y49959946-debug.github.io';

export default {
	async fetch(request, env) {
		const origin = request.headers.get('Origin') || '';
		const corsHeaders = {
			'Access-Control-Allow-Origin': origin === ALLOWED_ORIGIN ? origin : ALLOWED_ORIGIN,
			'Access-Control-Allow-Methods': 'GET, OPTIONS',
		};

		if (request.method === 'OPTIONS') {
			return new Response(null, { headers: corsHeaders });
		}

		const url = new URL(request.url);
		const endpoint = url.searchParams.get('endpoint'); // 'weather' 또는 'forecast'
		const q = url.searchParams.get('q');
		const lang = url.searchParams.get('lang') || 'kr';

		if (!['weather', 'forecast'].includes(endpoint) || !q) {
			return new Response(JSON.stringify({ error: 'endpoint(weather|forecast)와 q 파라미터가 필요해요.' }), {
				status: 400,
				headers: { ...corsHeaders, 'Content-Type': 'application/json' },
			});
		}

		const owmUrl = `https://api.openweathermap.org/data/2.5/${endpoint}`
			+ `?q=${encodeURIComponent(q)}&appid=${env.OPENWEATHER_API_KEY}&units=metric&lang=${encodeURIComponent(lang)}`;

		const owmRes = await fetch(owmUrl);
		const body = await owmRes.text();

		return new Response(body, {
			status: owmRes.status,
			headers: { ...corsHeaders, 'Content-Type': 'application/json' },
		});
	},
};
