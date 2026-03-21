// ============================================================
//  ShieldNet — domainScorer.js
//  Helpers de scoring (importado como script en background)
// ============================================================

// TLDs de alto riesgo (comunes en dominios de phishing)
const HIGH_RISK_TLDS = new Set([
  '.tk', '.ml', '.ga', '.cf', '.gq', // Freenom gratuitos
  '.xyz', '.top', '.click', '.link',
  '.work', '.date', '.racing', '.review',
  '.bid', '.trade', '.loan', '.stream'
]);

// TLDs gubernamentales/legítimos de México
const TRUSTED_TLDS = new Set([
  '.gob.mx', '.edu.mx', '.com.mx', '.org.mx',
  '.gov', '.edu', '.mil'
]);

function getTLDRisk(domain) {
  for (const tld of HIGH_RISK_TLDS) {
    if (domain.endsWith(tld)) return 'HIGH';
  }
  for (const tld of TRUSTED_TLDS) {
    if (domain.endsWith(tld)) return 'LOW';
  }
  return 'MEDIUM';
}

function hasExcessiveSubdomains(domain) {
  // ej: login.secure.paypal.verify.com → muy sospechoso
  const parts = domain.split('.');
  return parts.length > 4;
}

function hasSuspiciousPattern(domain) {
  const patterns = [
    /\d{2,}-/,           // muchos números con guión: paypal-123456.com
    /-\d+\./,            // guión + números: secure-892.com  
    /[a-z0-9]{25,}/,     // cadena aleatoria muy larga
    /login.*secure/i,    // login + secure en mismo dominio
    /verify.*account/i,  // verify + account
  ];
  return patterns.some(p => p.test(domain));
}

// Exportar como propiedades del objeto global (para importScripts)
self.getTLDRisk = getTLDRisk;
self.hasExcessiveSubdomains = hasExcessiveSubdomains;
self.hasSuspiciousPattern = hasSuspiciousPattern;
