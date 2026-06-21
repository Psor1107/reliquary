console.log("\n[FRONTEND - Node.js] Starting Next.js mock server...");

const apiKey = process.env.API_KEY;

if (apiKey) {
    console.log(`   [+] SSR API Endpoint secured with token: ${apiKey}`);
} else {
    console.error("   [-] FATAL: Missing API_KEY in environment.");
    process.exit(1);
}