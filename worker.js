/**
 * Cloudflare Worker - RSS Feed Proxy
 * Passthrough XML with CORS headers and edge caching
 */

const ALLOWED_DOMAINS = [
  'www.smpte.org',           // Added
  'theiabm.org',             // Added
  'blogs.telosalliance.com', // Added
  'www.haivision.com',       // Added
  'www.svgeurope.org',       // Added
  'www.newscaststudio.com',
  'www.tvtechnology.com',
  'www.broadcastbeat.com',
  'www.inbroadcast.com',
  'inbroadcast.com',
  'www.evertz.com',
  'evertz.com',
  'www.imaginecommunications.com',
  'imaginecommunications.com',
  'www.thebroadcastbridge.com',
  'www.vizrt.com',
  'routing.vizrt.com',
  'motionographer.com',
  'aws.amazon.com',
  'blog.frame.io',
  'krebsonsecurity.com',
  'www.darkreading.com',
  'www.bleepingcomputer.com',
  'www.securityweek.com',
  'feeds.feedburner.com',
  'cloud.google.com',
  'www.microsoft.com',
  'www.rossvideo.com',
  'www.harmonicinc.com',
  'www.broadcastbridge.com'
];

addEventListener('fetch', event => {
  event.respondWith(handleRequest(event.request));
});

async function handleRequest(request) {
  // Handle CORS preflight
  if (request.method === 'OPTIONS') {
    return new Response(null, {
      headers: {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type',
        'Access-Control-Max-Age': '86400'
      }
    });
  }

  // Extract feed URL from query parameter
  const url = new URL(request.url);
  const feedUrl = url.searchParams.get('url');

  if (!feedUrl) {
    return new Response('Missing url parameter', { 
      status: 400,
      headers: { 'Access-Control-Allow-Origin': '*' }
    });
  }

  // Validate domain
  let feedHostname;
  try {
    feedHostname = new URL(feedUrl).hostname;
  } catch (e) {
    return new Response('Invalid URL', { 
      status: 400,
      headers: { 'Access-Control-Allow-Origin': '*' }
    });
  }

  if (!ALLOWED_DOMAINS.includes(feedHostname)) {
    return new Response('Domain not allowed', { 
      status: 403,
      headers: { 'Access-Control-Allow-Origin': '*' }
    });
  }

  // Fetch the feed with browser-like headers
  try {
    const feedResponse = await fetch(feedUrl, {
      headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/rss+xml, application/xml, text/xml, */*',
        'Accept-Language': 'en-US,en;q=0.9',
        'Cache-Control': 'no-cache'
      },
      cf: {
        cacheTtl: 120,
        cacheEverything: true
      }
    });

    if (!feedResponse.ok) {
      return new Response(`Feed returned ${feedResponse.status}`, { 
        status: feedResponse.status,
        headers: { 'Access-Control-Allow-Origin': '*' }
      });
    }

    // Get the response body
    const feedText = await feedResponse.text();

    // Determine content type from original response
    const originalContentType = feedResponse.headers.get('content-type') || 'application/xml';

    // Return with CORS headers
    return new Response(feedText, {
      status: 200,
      headers: {
        'Content-Type': originalContentType,
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, OPTIONS',
        'Cache-Control': 'public, max-age=120',
        'X-Proxied-By': 'Cloudflare-Worker'
      }
    });

  } catch (error) {
    return new Response(`Fetch error: ${error.message}`, { 
      status: 502,
      headers: { 'Access-Control-Allow-Origin': '*' }
    });
  }
}