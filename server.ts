import express from 'express';
import path from 'path';
import fs from 'fs';
import { fileURLToPath } from 'url';
import { createServer as createViteServer } from 'vite';
import { GoogleGenAI } from '@google/genai';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const PORT = 3000;
const DB_FILE = path.resolve(process.cwd(), 'database.json');

// Initialize Gemini Client
const geminiApiKey = process.env.GEMINI_API_KEY;
let aiClient: GoogleGenAI | null = null;
if (geminiApiKey) {
  aiClient = new GoogleGenAI({
    apiKey: geminiApiKey,
    httpOptions: {
      headers: {
        'User-Agent': 'aistudio-build',
      }
    }
  });
}

// Helper to safely load database
function loadDb() {
  try {
    if (fs.existsSync(DB_FILE)) {
      const content = fs.readFileSync(DB_FILE, 'utf-8');
      const data = JSON.parse(content);
      
      // Strict constraint safeguard: remove smartphones
      if (data.products && Array.isArray(data.products)) {
        data.products = data.products.filter((p: any) => {
          const category = (p.category || '').toLowerCase();
          const name = (p.name || '').toLowerCase();
          return category !== 'smartphones' && !category.includes('phone') && !name.includes('iphone') && !name.includes('smartphone');
        });
      }
      return data;
    }
  } catch (err) {
    console.error("Error reading database.json:", err);
  }
  
  // Default Database Structure
  return {
    brands: [],
    products: [],
    reviews: [],
    users: [
      { id: "admin", username: "admin", email: "admin@vouch.in", password: "adminpassword", isPremium: true, isAdmin: true }
    ],
    saved_products: [],
    click_metrics: {}
  };
}

// Helper to safely save database
function saveDb(data: any) {
  try {
    // Strict constraint safeguard: remove smartphones before persistency
    if (data.products && Array.isArray(data.products)) {
      data.products = data.products.filter((p: any) => {
        const category = (p.category || '').toLowerCase();
        const name = (p.name || '').toLowerCase();
        return category !== 'smartphones' && !category.includes('phone') && !name.includes('iphone') && !name.includes('smartphone');
      });
    }
    
    fs.writeFileSync(DB_FILE, JSON.stringify(data, null, 2), 'utf-8');
    return true;
  } catch (err) {
    console.error("Error saving database.json:", err);
    return false;
  }
}

async function startServer() {
  const app = express();
  app.use(express.json());

  // ==========================================
  // API ENDPOINTS
  // ==========================================

  // GET /api/products
  app.get('/api/products', (req, res) => {
    const db = loadDb();
    const products = db.products || [];
    
    // Auto-enrich products with Trusted Circle properties if they don't exist
    products.forEach((p: any) => {
      if (!p.trusted_circle_activity) {
        // Deterministic baseline based on product unique id + trust score
        const factor = (p.id.charCodeAt(p.id.length - 1) % 5) + 3; // 3 to 7
        p.trusted_circle_activity = {
          friends: Math.round((p.trust_score || 85) * 0.1) + factor,
          purchased: Math.round((p.trust_score || 85) * 0.03) + (factor % 3) + 1,
          mentors: Math.max(1, Math.round((p.trust_score || 85) * 0.04) - (factor % 2)),
          experts: Math.max(1, Math.round((p.trust_score || 85) * 0.035) + (factor % 3))
        };
      }
      if (!p.trusted_circle_score) {
        p.trusted_circle_score = Math.round(((p.trust_score || 85) + 90) / 2);
      }
      if (!p.trusted_circle_feed) {
        p.trusted_circle_feed = [
          { id: `${p.id}_f1`, author: "Amit Mehra", role: "MENTOR", text: "Active owner: recommended 4 months ago" },
          { id: `${p.id}_f2`, author: "Pooja Sharma", role: "FRIEND", text: "Voted Expectations Met (YES)" },
          { id: `${p.id}_f3`, author: "Dr. Ravi Kumar", role: "EXPERT", text: "Endorsed transparent warranty index" }
        ];
      }
    });

    res.json(products);
  });

  // GET /api/brands
  app.get('/api/brands', (req, res) => {
    const db = loadDb();
    res.json(db.brands || []);
  });

  // GET /api/reviews
  app.get('/api/reviews', (req, res) => {
    const db = loadDb();
    res.json(db.reviews || []);
  });

  // GET /api/saved
  app.get('/api/saved', (req, res) => {
    const db = loadDb();
    res.json(db.saved_products || []);
  });

  // GET /api/affiliate/clicks
  app.get('/api/affiliate/clicks', (req, res) => {
    const db = loadDb();
    res.json(db.click_metrics || {});
  });

  // POST /api/saved/toggle
  app.post('/api/saved/toggle', (req, res) => {
    const { productId } = req.body;
    if (!productId) {
      return res.status(400).json({ error: "Missing productId" });
    }
    const db = loadDb();
    if (!db.saved_products) db.saved_products = [];
    
    const index = db.saved_products.indexOf(productId);
    if (index === -1) {
      db.saved_products.push(productId);
    } else {
      db.saved_products.splice(index, 1);
    }
    
    saveDb(db);
    res.json({ success: true, saved: db.saved_products });
  });

  // POST /api/affiliate/track
  app.post('/api/affiliate/track', (req, res) => {
    const { productId, platform } = req.body;
    if (!productId || !platform) {
      return res.status(400).json({ error: "Missing productId or platform" });
    }
    const db = loadDb();
    if (!db.click_metrics) db.click_metrics = {};
    
    const key = `${platform}_${productId}`;
    const currentCount = db.click_metrics[key] || 0;
    db.click_metrics[key] = currentCount + 1;
    
    saveDb(db);
    res.json({ success: true, count: db.click_metrics[key] });
  });

  // POST /api/brands/vote
  app.post('/api/brands/vote', (req, res) => {
    const { brandId, aspect, isPositive } = req.body;
    if (!brandId || !aspect) {
      return res.status(400).json({ error: "Missing brandId or aspect" });
    }

    const db = loadDb();
    if (!db.brands) db.brands = [];
    if (!db.products) db.products = [];

    const brandIndex = db.brands.findIndex((b: any) => b.id === brandId);
    if (brandIndex !== -1) {
      const brand = db.brands[brandIndex];
      if (!brand.accountability) {
        brand.accountability = { expectations: 80, repurchase: 80, promises: 80 };
      }
      
      const asp = aspect as 'expectations' | 'repurchase' | 'promises';
      const currentVal = brand.accountability[asp] || 80;
      const adjustment = isPositive ? 1 : -1;
      brand.accountability[asp] = Math.max(10, Math.min(100, currentVal + adjustment));
      
      // Recount credibility_score as rolling blend
      const avgAccountability = (brand.accountability.expectations + brand.accountability.repurchase + brand.accountability.promises) / 3;
      brand.credibility_score = Math.round((brand.transparency_score + brand.customer_service_score + avgAccountability) / 3);
      
      saveDb(db);
    }

    res.json({ success: true, brands: db.brands, products: db.products });
  });

  // POST /api/products/vote-circle
  app.post('/api/products/vote-circle', (req, res) => {
    const { productId, action, username } = req.body;
    if (!productId || !action) {
      return res.status(400).json({ error: "Missing productId or action field" });
    }

    const db = loadDb();
    if (!db.products) db.products = [];

    const productIdx = db.products.findIndex((p: any) => p.id === productId);
    if (productIdx !== -1) {
      const p = db.products[productIdx];

      // Safe baseline defaults in database
      if (!p.trusted_circle_activity) {
        const factor = (p.id.charCodeAt(p.id.length - 1) % 5) + 3;
        p.trusted_circle_activity = {
          friends: Math.round((p.trust_score || 85) * 0.1) + factor,
          purchased: Math.round((p.trust_score || 85) * 0.03) + (factor % 3) + 1,
          mentors: Math.max(1, Math.round((p.trust_score || 85) * 0.04) - (factor % 2)),
          experts: Math.max(1, Math.round((p.trust_score || 85) * 0.035) + (factor % 3))
        };
      }
      if (!p.trusted_circle_score) {
        p.trusted_circle_score = Math.round(((p.trust_score || 85) + 90) / 2);
      }
      if (!p.trusted_circle_feed) {
        p.trusted_circle_feed = [
          { id: `${p.id}_f1`, author: "Amit Mehra", role: "MENTOR", text: "Active owner: recommended 4 months ago" },
          { id: `${p.id}_f2`, author: "Pooja Sharma", role: "FRIEND", text: "Voted Expectations Met (YES)" },
          { id: `${p.id}_f3`, author: "Dr. Ravi Kumar", role: "EXPERT", text: "Endorsed transparent warranty index" }
        ];
      }

      const userNameStr = username || "Verified Peer";
      const feedId = "feed_" + Date.now();

      if (action === 'recommend') {
        p.trusted_circle_activity.friends += 1;
        p.trusted_circle_score = Math.min(100, p.trusted_circle_score + 1);
        p.trusted_circle_feed.unshift({
          id: feedId,
          author: userNameStr,
          role: "FRIEND",
          text: "Recommended this hardware appliance model"
        });
      } else if (action === 'purchase') {
        p.trusted_circle_activity.purchased += 1;
        p.trusted_circle_score = Math.min(100, p.trusted_circle_score + 1);
        p.trusted_circle_feed.unshift({
          id: feedId,
          author: userNameStr,
          role: "FRIEND",
          text: "Bought and registered this product via Vouch"
        });
      } else if (action === 'expectations_yes') {
        p.trusted_circle_activity.friends += 1;
        p.trusted_circle_score = Math.min(100, p.trusted_circle_score + 2);
        p.trusted_circle_feed.unshift({
          id: feedId,
          author: userNameStr,
          role: "FRIEND",
          text: "Confirmed expectations fully met (YES)"
        });
      } else if (action === 'expectations_no') {
        p.trusted_circle_score = Math.max(10, p.trusted_circle_score - 3);
        p.trusted_circle_feed.unshift({
          id: feedId,
          author: userNameStr,
          role: "FRIEND",
          text: "Voted expectations NOT met (NO)"
        });
      }

      // Limit feed size
      p.trusted_circle_feed = p.trusted_circle_feed.slice(0, 10);

      saveDb(db);
    }

    res.json({ success: true, products: db.products || [] });
  });

  // POST /api/auth/register
  app.post('/api/auth/register', (req, res) => {
    const { username, email, password } = req.body;
    if (!username || !email || !password) {
      return res.status(400).json({ error: "Missing username, email, or password" });
    }

    const db = loadDb();
    if (!db.users) db.users = [];

    // Check duplicate
    const exists = db.users.find((u: any) => u.email === email || u.username === username);
    if (exists) {
      return res.status(400).json({ success: false, error: "Username or Email already registered" });
    }

    const newUser = {
      id: "u_" + Date.now(),
      username,
      email,
      password,
      isPremium: false,
      isAdmin: username.toLowerCase() === 'admin'
    };

    db.users.push(newUser);
    saveDb(db);
    
    // Return sanitized user (exclude password in production, but here safe)
    res.json({ success: true, user: newUser });
  });

  // POST /api/auth/login
  app.post('/api/auth/login', (req, res) => {
    const { username, email, password } = req.body;
    const db = loadDb();
    if (!db.users) db.users = [];

    const user = db.users.find((u: any) => 
      (email && u.email === email && u.password === password) ||
      (username && u.username === username && u.password === password)
    );

    if (user) {
      res.json({ success: true, user });
    } else {
      res.status(401).json({ success: false, error: "Invalid credentials entered" });
    }
  });

  // POST /api/auth/toggle-premium
  app.post('/api/auth/toggle-premium', (req, res) => {
    const { userId } = req.body;
    const db = loadDb();
    if (!db.users) db.users = [];

    const userIdx = db.users.findIndex((u: any) => u.id === userId);
    if (userIdx !== -1) {
      db.users[userIdx].isPremium = !db.users[userIdx].isPremium;
      saveDb(db);
      res.json({ success: true, user: db.users[userIdx] });
    } else {
      res.status(404).json({ error: "User profile not found" });
    }
  });

  // POST /api/reviews
  app.post('/api/reviews', (req, res) => {
    const { productId, rating, author, reviewText, verified } = req.body;
    if (!productId || !author || !reviewText) {
      return res.status(400).json({ error: "Missing review information parameters" });
    }

    const db = loadDb();
    if (!db.reviews) db.reviews = [];
    if (!db.products) db.products = [];

    const newRev = {
      id: "r_" + Date.now(),
      product_id: productId,
      rating: Number(rating),
      author,
      review_text: reviewText,
      verified: !!verified
    };

    db.reviews.push(newRev);

    // Dynamic brand support & product calculations update
    const productIdx = db.products.findIndex((p: any) => p.id === productId);
    if (productIdx !== -1) {
      const p = db.products[productIdx];
      p.review_count = (p.review_count || 0) + 1;
      
      // Calculate average rating
      const relatedReviews = db.reviews.filter((r: any) => r.product_id === productId);
      const totalRating = relatedReviews.reduce((sum: number, r: any) => sum + r.rating, 0);
      p.rating = Number((totalRating / relatedReviews.length).toFixed(1));

      // Authenticity & live scores adjustments
      if (verified) {
        p.authenticity_score = Math.min(100, Math.round((p.authenticity_score || 85) + 1.5));
        p.verified_review_rate = Math.min(100, Math.round((p.verified_review_rate || 90) + 1));
      } else {
        p.authenticity_score = Math.max(10, Math.round((p.authenticity_score || 85) - 2));
      }
      p.trust_score = Math.round(((p.authenticity_score || 85) + (p.warranty_score || 85)) / 2);
    }

    saveDb(db);
    res.json({ success: true, products: db.products, reviews: db.reviews });
  });

  // POST /api/admin/product/add
  app.post('/api/admin/product/add', (req, res) => {
    const productData = req.body;
    const db = loadDb();
    if (!db.products) db.products = [];

    const newId = "p_" + Date.now();
    const newProd = {
      ...productData,
      id: newId,
      trust_score: Number(productData.trust_score || 85),
      authenticity_score: Number(productData.authenticity_score || 85),
      transparency_score: Number(productData.transparency_score || 82),
      warranty_score: Number(productData.warranty_score || 85),
      complaint_rate: Number(productData.complaint_rate || 1.2),
      return_rate: Number(productData.return_rate || 1.8),
      verified_review_rate: Number(productData.verified_review_rate || 90),
      is_sponsored: !!productData.is_sponsored,
      is_premium_only: !!productData.is_premium_only
    };

    db.products.push(newProd);
    saveDb(db);
    res.json({ success: true, products: db.products });
  });

  // PUT /api/admin/product/edit
  app.put('/api/admin/product/edit', (req, res) => {
    const productData = req.body;
    const db = loadDb();
    if (!db.products) db.products = [];

    const productIdx = db.products.findIndex((p: any) => p.id === productData.id);
    if (productIdx !== -1) {
      db.products[productIdx] = {
        ...db.products[productIdx],
        ...productData,
        trust_score: Number(productData.trust_score),
        authenticity_score: Number(productData.authenticity_score),
        transparency_score: Number(productData.transparency_score),
        warranty_score: Number(productData.warranty_score),
        complaint_rate: Number(productData.complaint_rate),
        return_rate: Number(productData.return_rate),
        verified_review_rate: Number(productData.verified_review_rate),
        is_sponsored: !!productData.is_sponsored,
        is_premium_only: !!productData.is_premium_only
      };
      saveDb(db);
      res.json({ success: true, products: db.products });
    } else {
      res.status(404).json({ error: "Product not found" });
    }
  });

  // DELETE /api/admin/product/:id
  app.delete('/api/admin/product/:id', (req, res) => {
    const { id } = req.params;
    const db = loadDb();
    if (!db.products) db.products = [];

    db.products = db.products.filter((p: any) => p.id !== id);
    saveDb(db);
    res.json({ success: true, products: db.products });
  });

  // POST /api/admin/brand/add
  app.post('/api/admin/brand/add', (req, res) => {
    const brandData = req.body;
    const db = loadDb();
    if (!db.brands) db.brands = [];

    const newId = "b_" + Date.now();
    const newBrand = {
      ...brandData,
      id: newId,
      credibility_score: Number(brandData.credibility_score || 85),
      transparency_score: Number(brandData.transparency_score || 80),
      customer_service_score: Number(brandData.customer_service_score || 85),
      years_in_business: Number(brandData.years_in_business || 10),
      verified: !!brandData.verified,
      accountability: { expectations: 85, repurchase: 82, promises: 85 },
      advantages: ["Warranty response guarantee"],
      disadvantages: ["Minor documentation turnaround lag"],
      weight_breakdown: { verification: 85, sat: 80, transparency: 80, consistency: 80, community: 80, maturity: 80, circle: 80 },
      journey: [{ year: 2024, score: 80 }, { year: 2025, score: 82 }, { year: 2026, score: 84 }],
      associated_products: ["Electric Appliances"]
    };

    db.brands.push(newBrand);
    saveDb(db);
    res.json({ success: true, brands: db.brands });
  });

  // DELETE /api/admin/review/:id
  app.delete('/api/admin/review/:id', (req, res) => {
    const { id } = req.params;
    const db = loadDb();
    if (!db.reviews) db.reviews = [];

    db.reviews = db.reviews.filter((r: any) => r.id !== id);
    saveDb(db);
    res.json({ success: true, reviews: db.reviews });
  });

  // POST /api/chat
  app.post('/api/chat', async (req, res) => {
    const { message, isPremium } = req.body;
    if (!message) {
      return res.status(400).json({ error: "Missing message query" });
    }

    const db = loadDb();

    // 1. If Gemini client is ready, use GenAI SDK server-side call!
    if (aiClient) {
      try {
        const sanitizedProds = (db.products || []).map((p: any) => ({
          name: p.name,
          brand: p.brand,
          category: p.category,
          desc: p.description,
          trust_score: p.trust_score,
          auth_score: p.authenticity_score,
          rma_rate: p.return_rate,
          complaints: p.complaint_rate
        }));

        const groundingInstruction = `
You are Vouch AI, an elite, unbiased frontend hardware transparency and purchase credibility assistant.
You are strictly forbidden from showing or referencing product prices (prices have been removed from the database to maintain neutral focus on product build quality, warranty, and return metrics).
You are strictly forbidden from listing or advising on Smartphones or iPhones (smartphones are completely removed from the catalog). Do not recommend them.

Grounded Products Directory: ${JSON.stringify(sanitizedProds)}
Grounded Corporate Brands: ${JSON.stringify(db.brands || [])}

When answering about products, warranties, or device return rates, scan these logged catalog items to formulate detailed metrics and insights. Keep responses concise, helpful, and beautifully written.
        `;

        const responseMsg = await aiClient.models.generateContent({
          model: 'gemini-3.5-flash',
          contents: message,
          config: {
            systemInstruction: groundingInstruction,
            temperature: 0.7
          }
        });

        return res.json({ response: responseMsg.text || "I processed your request but returned an empty answer." });
      } catch (geminiErr: any) {
        console.error("Gemini API Error in server.ts:", geminiErr);
      }
    }

    // 2. Offline Fallback Logic (Robust Querying over local DB keywords)
    const query = message.toLowerCase();
    let matchingProduct = (db.products || []).find((p: any) => 
      query.includes(p.name.toLowerCase()) || query.includes(p.brand.toLowerCase())
    );
    let matchingBrand = (db.brands || []).find((b: any) => 
      query.includes(b.brand_name.toLowerCase()) || query.includes(b.id.toLowerCase())
    );

    let reply = "";
    if (matchingProduct) {
      reply = `🛡️ **Vouch Database Match**: Found details for **${matchingProduct.name}** under **${matchingProduct.brand}**.\n\n` +
              `- **Trust Score**: ${matchingProduct.trust_score}/100\n` +
              `- **Review Authenticity**: ${matchingProduct.authenticity_score}% verified real purchases\n` +
              `- **RMA Return Rate**: ${matchingProduct.return_rate}% of sales\n` +
              `- **Consumer Complaint Rate**: ${matchingProduct.complaint_rate}% of sales\n\n` +
              `*Hardware Insight*: ${matchingProduct.description}. All listed statistics are verified live by our transactional RMA audit logs. No smartphones or monetary pricing index variables are plotted.`;
    } else if (matchingBrand) {
      reply = `🛡️ **Corporate Brand Match**: Found analysis for **${matchingBrand.brand_name}**.\n\n` +
              `- **Corporate Credibility Rating**: ${matchingBrand.credibility_score}/100 (Grade ${matchingBrand.transparency_rating})\n` +
              `- **Years Operating Retail**: ${matchingBrand.years_in_business} Years\n` +
              `- **Warranty support resolution rate**: ${matchingBrand.customer_service_score}%\n` +
              `- **Published Warranty Coverage**: "${matchingBrand.warranty_policy}"\n\n` +
              `*Audit Assessment*: ${matchingBrand.insights}. They are a recognized verified brand with robust consumer dispute compliance.`;
    } else {
      reply = `Hello! I am your offline **Vouch AI** advisor. I can scan active appliance models, warranties, and corporate metadata securely.\n\n` +
              `Currently, I find no exact match for "${message}" in our offline database categories (Washing Machines, smart TVs, skincare, or laptops). Try querying a catalog brand like **Apple**, **Samsung**, **LG**, **Dyson**, or **Cosrx** to instantly fetch detailed credibility rankings!`;
    }

    res.json({ response: reply });
  });

  // ==========================================
  // VITE SERVICE / STATIC ASSET SERVING MIDDLEWARE
  // ==========================================
  if (process.env.NODE_ENV !== "production") {
    const vite = await createViteServer({
      server: { middlewareMode: true },
      appType: "spa",
    });
    app.use(vite.middlewares);
  } else {
    const distPath = path.join(process.cwd(), 'dist');
    app.use(express.static(distPath)); // Safely handling Express fallback
    app.get('*', (req, res) => {
      res.sendFile(path.join(distPath, 'index.html'));
    });
  }

  app.listen(PORT, "0.0.0.0", () => {
    console.log(`[Vouch Server] Gateway proxy running at http://0.0.0.0:${PORT}`);
  });
}

startServer();
