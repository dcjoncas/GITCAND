from __future__ import annotations

import base64
import csv
import io
import json
import os
import re
import time
from dataclasses import dataclass, asdict
from typing import Any, Dict, Iterable, List, Optional

import requests
from flask import Flask, jsonify, render_template_string, request, Response

try:
    from openai import OpenAI
except Exception:
    OpenAI = None

try:
    import psycopg
except Exception:
    psycopg = None

app = Flask(__name__)
REST_BASE = "https://api.github.com"
GRAPHQL_URL = "https://api.github.com/graphql"
DEVREADY_URL = "https://www.devready.io"
DEVREADY_EMAIL = "recruiting@devready.io"
DEFAULT_QUERIES = ['"open to work" in:bio','"available for work" in:bio','"looking for opportunities" in:bio','"seeking new role" in:bio','(freelance OR contractor OR contract) in:bio']
SKILL_SYNONYMS = {
    "javascript": ["javascript", "js", "ecmascript"], "typescript": ["typescript", "ts"], "react": ["react", "reactjs", "react.js"],
    "angular": ["angular", "angularjs"], "vue": ["vue", "vuejs", "vue.js"], "next.js": ["next.js", "nextjs", "next js"],
    "node": ["node", "nodejs", "node.js"], "html": ["html", "html5"], "css": ["css", "css3"], "scss": ["scss", "sass"],
    "tailwind": ["tailwind", "tailwindcss"], "material ui": ["material ui", "mui"], "storybook": ["storybook"], "jest": ["jest"],
    "cypress": ["cypress"], "playwright": ["playwright"], "redux": ["redux"], "graphql": ["graphql"], "rest": ["rest", "restful"],
    "api": ["api", "apis"], "figma": ["figma"], "accessibility": ["accessibility", "a11y", "wcag"],
    "responsive design": ["responsive", "responsive design", "mobile first", "mobile-first"], "frontend": ["frontend", "front-end", "front end"],
    "backend": ["backend", "back-end", "back end"], "full stack": ["full stack", "full-stack", "fullstack"], "aws": ["aws"],
    "azure": ["azure"], "gcp": ["gcp", "google cloud"], "python": ["python"], "java": ["java"], "sql": ["sql", "postgres", "postgresql", "mysql"]
}
SKILL_GROUPS = {
    "languages": ["javascript", "typescript", "html", "css", "scss", "python", "java", "sql"],
    "frontend_frameworks": ["react", "angular", "vue", "next.js"],
    "styling_ui": ["tailwind", "material ui", "figma", "accessibility", "responsive design"],
    "data_api": ["graphql", "rest", "api", "redux"],
    "testing": ["jest", "cypress", "playwright"],
    "platform": ["frontend", "backend", "full stack", "node", "aws", "azure", "gcp"],
}
ROLE_HINTS = {
    "frontend": ["frontend", "react", "typescript", "javascript", "html", "css", "ui", "ux"],
    "backend": ["backend", "python", "java", "node", "api", "sql"],
    "full stack": ["full stack", "frontend", "backend", "react", "typescript", "python", "api"],
}
AVAILABILITY_PATTERNS = [r"\bopen to work\b", r"\bavailable for work\b", r"\blooking for opportunities\b", r"\bseeking (a )?new role\b", r"\bopen to opportunities\b", r"\bfreelance\b", r"\bcontract(or)?\b"]
EMAIL_REGEX = re.compile(r'([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})')
LINKEDIN_REGEX = re.compile(r'(https?://(?:www\.)?linkedin\.com/[^\s)]+)', re.I)

HTML = """<!DOCTYPE html><html lang='en'><head><meta charset='UTF-8'/><meta name='viewport' content='width=device-width, initial-scale=1.0'/><title>DevReady Candidate Dashboard</title><style>
:root{--bg:#07130d;--panel:#10251a;--panel2:#163624;--text:#effff5;--muted:#9bc2ae;--accent:#1ed760;--accent2:#57f28f;--warn:#ffcc66;--danger:#ff8e8e;--radius:18px;--shadow:0 18px 45px rgba(0,0,0,.25)}
*{box-sizing:border-box}body{margin:0;font-family:Inter,Segoe UI,Arial,sans-serif;background:linear-gradient(180deg,#07130d 0%,#0b1711 100%);color:var(--text)}
.wrap{max-width:1700px;margin:0 auto;padding:24px}.hero,.card{background:rgba(16,37,26,.94);border:1px solid rgba(255,255,255,.08);border-radius:24px;box-shadow:var(--shadow)}.hero{padding:24px 26px;margin-bottom:20px;background:linear-gradient(135deg,rgba(30,215,96,.20),rgba(87,242,143,.10));display:flex;justify-content:space-between;gap:20px}.hero h1{margin:0 0 8px 0}.hero p{margin:0;color:var(--muted);max-width:900px;line-height:1.5}.brand{display:inline-block;padding:10px 14px;border-radius:999px;background:rgba(30,215,96,.15);color:var(--accent);font-weight:900;margin-bottom:10px}.actions{display:flex;gap:10px;flex-wrap:wrap}.btn{display:inline-flex;align-items:center;gap:8px;border:none;border-radius:14px;padding:12px 16px;font-weight:800;cursor:pointer;background:var(--accent);color:#062010}.btn.secondary{background:#1d3c2b;color:var(--text);border:1px solid rgba(255,255,255,.08)}
.grid{display:grid;grid-template-columns:1.1fr 1fr 1fr 1fr;gap:18px;margin-bottom:18px}.metric{padding:18px}.metric .label{font-size:13px;color:var(--muted);margin-bottom:8px}.metric .value{font-size:34px;font-weight:900}.metric .sub{font-size:13px;color:var(--muted);margin-top:8px}.layout{display:grid;grid-template-columns:430px 1fr 390px;gap:18px;align-items:start}.card{padding:18px}.section{font-size:13px;font-weight:800;letter-spacing:.35px;color:var(--muted);text-transform:uppercase;margin-bottom:12px}label{display:block;font-size:13px;color:var(--muted);margin:0 0 8px 0}.input,textarea,select{width:100%;padding:12px 14px;border-radius:14px;border:1px solid rgba(255,255,255,.10);background:#0b1b13;color:var(--text);outline:none}textarea{min-height:110px;resize:vertical}.two{display:grid;grid-template-columns:1fr 1fr;gap:12px}.three{display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px}.group{margin-bottom:16px}.status{font-size:13px;color:var(--muted);line-height:1.5}.chip{display:inline-flex;padding:7px 10px;border-radius:999px;background:#1d3c2b;border:1px solid rgba(255,255,255,.06);font-size:12px;margin:0 6px 6px 0}.chips{display:flex;flex-wrap:wrap}.group-box{padding:12px;border-radius:14px;background:#0b1b13;border:1px solid rgba(255,255,255,.06)}.bars{display:grid;gap:12px}.bar-row .head{display:flex;justify-content:space-between;font-size:13px;margin-bottom:6px}.bar{height:12px;background:#0a1711;border:1px solid rgba(255,255,255,.05);border-radius:999px;overflow:hidden}.bar>span{display:block;height:100%;background:linear-gradient(90deg,var(--accent),var(--accent2))}.table-wrap{overflow:auto;border-radius:16px;border:1px solid rgba(255,255,255,.08)}table{width:100%;min-width:1400px;border-collapse:collapse;background:#0f2017}th,td{padding:14px 12px;text-align:left;border-bottom:1px solid rgba(255,255,255,.07);vertical-align:top}th{position:sticky;top:0;background:#143423;font-size:12px;color:#c8f8d9;text-transform:uppercase}tr:hover td{background:#153226}tr.selected td{background:#183a2a}.score{display:inline-flex;min-width:64px;justify-content:center;align-items:center;padding:8px 10px;border-radius:999px;font-weight:900}.high{background:rgba(87,242,143,.14);color:var(--accent2)}.mid{background:rgba(255,204,102,.13);color:var(--warn)}.low{background:rgba(255,142,142,.12);color:var(--danger)}.tiny{font-size:12px;color:var(--muted)}.link{color:#8ff7b4;text-decoration:none}.link:hover{text-decoration:underline}.empty{padding:38px 18px;text-align:center;color:var(--muted);border:1px dashed rgba(255,255,255,.12);border-radius:16px;background:#0b1b13}.profile{position:sticky;top:24px}.profile-name{font-size:24px;font-weight:900}.profile-handle{font-size:13px;color:var(--muted)}.profile-section{margin-top:16px;padding-top:14px;border-top:1px solid rgba(255,255,255,.08)}.profile-label{font-size:12px;color:var(--muted);text-transform:uppercase;margin-bottom:8px}.profile-actions{display:flex;gap:10px;flex-wrap:wrap;margin-top:14px}@media (max-width:1450px){.layout{grid-template-columns:430px 1fr}.profile{grid-column:1 / -1;position:static}}@media (max-width:1200px){.grid{grid-template-columns:1fr 1fr}.layout{grid-template-columns:1fr}.hero{flex-direction:column}}@media (max-width:760px){.grid,.two,.three{grid-template-columns:1fr}.wrap{padding:14px}}</style></head><body>
<div class='wrap'><div class='hero'><div><div class='brand'>DEVREADY</div><h1>Candidate Mining Dashboard</h1><p>Paste a job description, parse it into a structured role profile with AI, populate the search stack automatically, then mine GitHub candidates and review them in one flow.</p><p class='tiny' style='margin-top:8px'>Website: <a class='link' href='https://www.devready.io' target='_blank'>www.devready.io</a></p></div><div class='actions'><button class='btn' id='parseAndSearch'>Add JD and Find Candidates</button><button class='btn secondary' id='runSearchOnly'>Run Search Only</button><button class='btn secondary' id='exportCsv'>Download Results CSV</button></div></div>
<div class='grid'><div class='card metric'><div class='label'>Candidates in view</div><div class='value' id='metricCount'>0</div><div class='sub' id='metricSummary'>Paste a JD or run a search to begin.</div></div><div class='card metric'><div class='label'>Average score</div><div class='value' id='metricAvg'>0</div><div class='sub'>Current filtered population</div></div><div class='card metric'><div class='label'>Availability signals</div><div class='value' id='metricAvail'>0</div><div class='sub'>Public open-to-work wording</div></div><div class='card metric'><div class='label'>Public contact paths</div><div class='value' id='metricContact'>0</div><div class='sub'>Website, LinkedIn, or public email found</div></div></div>
<div class='layout'><aside><div class='card'><div class='section'>Job Description Intake</div><div class='group'><label for='jobDescription'>Paste job description</label><textarea id='jobDescription' class='input' placeholder='Paste a frontend developer JD here...'></textarea></div><div class='two'><div class='group'><label for='roleHint'>Role focus</label><select id='roleHint'><option value='frontend'>Frontend</option><option value='full stack'>Full Stack</option><option value='backend'>Backend</option><option value='auto'>Auto detect</option></select></div><div class='group'><label for='location'>Location</label><input id='location' class='input' value='canada'/></div></div><div class='group-box'><div class='section' style='margin-bottom:10px'>Parsed Skill Groups</div><div id='parsedGroups' class='tiny'>No job description parsed yet.</div></div></div>
<div class='card' style='margin-top:18px'><div class='section'>Search Parameters</div><div class='group'><label for='phrase'>Phrase in bio</label><input id='phrase' class='input' value='open to work'/></div><div class='group'><label for='stacks'>Stack / tool set</label><input id='stacks' class='input' value='react,typescript,javascript,frontend,html,css'/></div><div class='group'><label for='keywords'>Scoring keywords</label><input id='keywords' class='input' value='react,typescript,javascript,frontend,html,css'/></div><div class='group'><label for='extraQuery'>Extra GitHub query terms</label><input id='extraQuery' class='input' placeholder='followers:>10 repos:>5'/></div><div class='three'><div class='group'><label for='perQueryLimit'>Per page</label><input id='perQueryLimit' class='input' type='number' min='1' max='100' value='30'/></div><div class='group'><label for='pages'>Pages</label><input id='pages' class='input' type='number' min='1' max='10' value='1'/></div><div class='group'><label for='maxEnrich'>Max enrich</label><input id='maxEnrich' class='input' type='number' min='1' max='200' value='50'/></div></div><div class='group'><label for='minScoreServer'>Server-side min score</label><input id='minScoreServer' class='input' type='number' min='0' max='100' value='0'/></div><div class='status' id='runStatus'>Paste a job description and click <strong>Add JD and Find Candidates</strong>.</div></div>
<div class='card' style='margin-top:18px'><div class='section'>Client Filters</div><div class='group'><label for='searchText'>Search results</label><input id='searchText' class='input' placeholder='name, login, bio, keywords, location...'/></div><div class='group'><label for='minScore'>Minimum score</label><div class='two'><input id='minScore' type='range' min='0' max='100' value='0'/><div class='chip' id='minScoreValue'>0</div></div></div><div class='two'><div class='group'><label for='availabilityOnly'>Availability</label><select id='availabilityOnly'><option value='all'>Show all</option><option value='yes'>Only yes</option><option value='no'>Only no</option></select></div><div class='group'><label for='contactOnly'>Public contact path</label><select id='contactOnly'><option value='all'>Show all</option><option value='yes'>Only yes</option><option value='no'>Only no</option></select></div></div><div class='group'><label for='sortBy'>Sort by</label><select id='sortBy'><option value='score_desc'>Score high to low</option><option value='score_asc'>Score low to high</option><option value='followers_desc'>Followers high to low</option><option value='repos_desc'>Public repos high to low</option><option value='name_asc'>Name A–Z</option><option value='login_asc'>Login A–Z</option></select></div><div class='group'><label>Keyword chips</label><div id='keywordChips' class='chips'></div></div></div></aside>
<section><div class='two' style='margin-bottom:18px'><div class='card'><div class='section'>Top Skill Keywords</div><div id='keywordBars' class='bars'></div></div><div class='card'><div class='section'>Top Locations</div><div id='locationBars' class='bars'></div></div></div><div class='card'><div class='section'>Candidate Table</div><div class='table-wrap'><table><thead><tr><th>Candidate</th><th>Score</th><th>Availability</th><th>Followers</th><th>Repos</th><th>Location</th><th>Keywords</th><th>Best public contact</th><th>Contact details</th><th>Profile</th><th>Notes</th></tr></thead><tbody id='candidateBody'></tbody></table></div><div id='emptyState' class='empty'>No candidates loaded yet.</div></div></section>
<aside class='profile'><div class='card'><div class='section'>Selected Candidate Profile</div><div id='profilePanel' class='empty'>Select a candidate to view the profile and generate an outreach email.</div></div></aside></div></div>
<script>
const DEVREADY_EMAIL='recruiting@devready.io', DEVREADY_SITE='https://www.devready.io'; const state={raw:[],filtered:[],activeKeyword:null,selectedLogin:null,parsedGroups:{}};
const els={jobDescription:document.getElementById('jobDescription'),roleHint:document.getElementById('roleHint'),parsedGroups:document.getElementById('parsedGroups'),parseAndSearch:document.getElementById('parseAndSearch'),runSearchOnly:document.getElementById('runSearchOnly'),exportCsv:document.getElementById('exportCsv'),phrase:document.getElementById('phrase'),location:document.getElementById('location'),stacks:document.getElementById('stacks'),keywords:document.getElementById('keywords'),extraQuery:document.getElementById('extraQuery'),perQueryLimit:document.getElementById('perQueryLimit'),pages:document.getElementById('pages'),maxEnrich:document.getElementById('maxEnrich'),minScoreServer:document.getElementById('minScoreServer'),runStatus:document.getElementById('runStatus'),searchText:document.getElementById('searchText'),minScore:document.getElementById('minScore'),minScoreValue:document.getElementById('minScoreValue'),availabilityOnly:document.getElementById('availabilityOnly'),contactOnly:document.getElementById('contactOnly'),sortBy:document.getElementById('sortBy'),keywordChips:document.getElementById('keywordChips'),keywordBars:document.getElementById('keywordBars'),locationBars:document.getElementById('locationBars'),candidateBody:document.getElementById('candidateBody'),emptyState:document.getElementById('emptyState'),metricCount:document.getElementById('metricCount'),metricSummary:document.getElementById('metricSummary'),metricAvg:document.getElementById('metricAvg'),metricAvail:document.getElementById('metricAvail'),metricContact:document.getElementById('metricContact'),profilePanel:document.getElementById('profilePanel')};
function scoreClass(s){return s>=60?'high':s>=30?'mid':'low'} function splitKeywords(v){return String(v||'').split(',').map(x=>x.trim()).filter(Boolean)} function includesText(c,q){return [c.login,c.name,c.bio,c.location,c.company,c.website_url,c.matching_keywords,c.top_languages,c.notes,c.best_contact_method,c.public_email,c.linkedin_url,c.contact_paths].join(' ').toLowerCase().includes(q)}
function getCounts(rows,field){const m=new Map(); rows.forEach(r=>{const vals=field==='matching_keywords'?splitKeywords(r.matching_keywords):[(r.location||'Unknown').trim()||'Unknown']; vals.forEach(v=>m.set(v,(m.get(v)||0)+1))}); return [...m.entries()].sort((a,b)=>b[1]-a[1])}
function renderBars(el,items){el.innerHTML=''; if(!items.length){el.innerHTML='<div class="tiny">No data available.</div>'; return} const max=items[0][1]||1; items.slice(0,8).forEach(([label,value])=>{const row=document.createElement('div'); row.className='bar-row'; row.innerHTML=`<div class="head"><span>${label}</span><span>${value}</span></div><div class="bar"><span style="width:${(value/max)*100}%"></span></div>`; el.appendChild(row)})}
function renderKeywordChips(){const counts=getCounts(state.raw,'matching_keywords').slice(0,18); els.keywordChips.innerHTML=''; if(!counts.length){els.keywordChips.innerHTML='<span class="tiny">No keyword data loaded yet.</span>'; return} counts.forEach(([keyword,count])=>{const chip=document.createElement('button'); chip.className='chip'; chip.style.cursor='pointer'; chip.style.background=state.activeKeyword===keyword?'rgba(87,242,143,.18)':''; chip.style.color=state.activeKeyword===keyword?'var(--accent2)':''; chip.textContent=`${keyword} (${count})`; chip.onclick=()=>{state.activeKeyword=state.activeKeyword===keyword?null:keyword; applyFilters()}; els.keywordChips.appendChild(chip)})}
function renderMetrics(){const rows=state.filtered,count=rows.length,avg=count?(rows.reduce((s,r)=>s+r.score,0)/count).toFixed(1):'0',avail=rows.filter(r=>r.availability_signal).length,contact=rows.filter(r=>r.has_public_contact).length; els.metricCount.textContent=count; els.metricAvg.textContent=avg; els.metricAvail.textContent=avail; els.metricContact.textContent=contact; els.metricSummary.textContent=count?`${avail} with availability signals, ${contact} with a public contact path.`:'No candidates match the current filters.'}
function buildEmailLink(c){const name=c.name||c.login||'there', target=c.public_email||DEVREADY_EMAIL; const body=`Hi ${name},\n\nI am from DevReady and want to see if you are interested in joining our community and interviewing for a position we have open for you.\n\nWebsite: www.devready.io\nEmail: recruiting@devready.io\n\nBest,\nDevReady Recruiting`; return `mailto:${target}?subject=${encodeURIComponent(`DevReady opportunity for ${name}`)}&body=${encodeURIComponent(body)}`}
function renderParsedGroups(groups){const keys=Object.keys(groups||{}).filter(k=>(groups[k]||[]).length); if(!keys.length){els.parsedGroups.innerHTML='<div class="tiny">No grouped skills found yet.</div>'; return} els.parsedGroups.innerHTML=keys.map(k=>`<div style="margin-bottom:10px"><div class="tiny" style="margin-bottom:6px;text-transform:uppercase">${k.replaceAll('_',' ')}</div><div>${groups[k].map(v=>`<span class="chip">${v}</span>`).join(' ')}</div></div>`).join('')}
function renderProfile(){const c=state.raw.find(r=>r.login===state.selectedLogin)||state.filtered[0]||null; if(!c){els.profilePanel.className='empty'; els.profilePanel.innerHTML='Select a candidate to view the profile and generate an outreach email.'; return} const chips=splitKeywords(c.matching_keywords).map(k=>`<span class="chip">${k}</span>`).join(' ')||'<span class="tiny">No matched keywords captured.</span>'; els.profilePanel.className=''; els.profilePanel.innerHTML=`<div class="profile-name">${c.name||c.login}</div><div class="profile-handle">@${c.login}</div><div style="margin-top:8px"><span class="score ${scoreClass(c.score)}">${c.score}</span></div><div style="margin-top:14px;line-height:1.55">${c.bio||'No public bio available.'}</div><div class="profile-section"><div class="profile-label">Location</div><div>${c.location||'—'}</div></div><div class="profile-section"><div class="profile-label">Company</div><div>${c.company||'—'}</div></div><div class="profile-section"><div class="profile-label">Top languages</div><div>${c.top_languages||'—'}</div></div><div class="profile-section"><div class="profile-label">Matched keywords</div><div>${chips}</div></div><div class="profile-section"><div class="profile-label">Pinned repositories</div><div>${c.pinned_repo_names||'—'}</div></div><div class="profile-section"><div class="profile-label">Recent repositories</div><div>${c.recent_repo_names||'—'}</div></div><div class="profile-section"><div class="profile-label">Public contact path</div><div>${c.best_contact_method||'GitHub profile only'}</div><div class="tiny" style="margin-top:8px">${c.website_url?`Website: <a class="link" href="${c.website_url}" target="_blank">Open</a><br>`:''}${c.linkedin_url?`LinkedIn: <a class="link" href="${c.linkedin_url}" target="_blank">Open</a><br>`:''}${c.public_email?`Email: ${c.public_email}`:''}</div></div><div class="profile-section"><div class="profile-label">DevReady outreach</div><div>DevReady website: <a class="link" href="${DEVREADY_SITE}" target="_blank">www.devready.io</a><br>DevReady recruiting: <a class="link" href="mailto:${DEVREADY_EMAIL}">${DEVREADY_EMAIL}</a></div><div class="profile-actions"><a class="btn" href="${buildEmailLink(c)}">Generate Email</a><a class="btn secondary" href="${c.profile_url||'#'}" target="_blank">Open GitHub</a></div></div>`}
function renderTable(){const rows=state.filtered; els.candidateBody.innerHTML=''; els.emptyState.style.display=rows.length?'none':'block'; rows.forEach(r=>{const tr=document.createElement('tr'); if(state.selectedLogin===r.login) tr.classList.add('selected'); const badges=[]; if(r.website_url) badges.push(`<a class="chip link" href="${r.website_url}" target="_blank">Website</a>`); if(r.linkedin_url) badges.push(`<a class="chip link" href="${r.linkedin_url}" target="_blank">LinkedIn</a>`); if(r.public_email) badges.push(`<span class="chip">${r.public_email}</span>`); if(!badges.length) badges.push('<span class="tiny">No explicit public contact path found</span>'); tr.innerHTML=`<td><div><a class="link" href="${r.profile_url||'#'}" target="_blank">${r.name||r.login}</a></div><div class="tiny">@${r.login}</div><div class="tiny">${r.company||''}</div></td><td><span class="score ${scoreClass(r.score)}">${r.score}</span></td><td>${r.availability_signal?'<span class="link">Yes</span>':'<span class="tiny">No</span>'}</td><td>${r.followers}</td><td>${r.public_repos}</td><td>${r.location||'<span class="tiny">—</span>'}</td><td>${r.matching_keywords||'<span class="tiny">—</span>'}</td><td>${r.best_contact_method||'<span class="tiny">Profile only</span>'}</td><td>${badges.join(' ')}</td><td><button class="btn secondary" data-login="${r.login}" style="padding:8px 10px">View Profile</button></td><td>${r.notes||'<span class="tiny">—</span>'}</td>`; tr.addEventListener('click',evt=>{if(evt.target.closest('a')||evt.target.closest('button')) return; state.selectedLogin=r.login; renderTable(); renderProfile()}); els.candidateBody.appendChild(tr)}); els.candidateBody.querySelectorAll('button[data-login]').forEach(btn=>btn.addEventListener('click',evt=>{evt.stopPropagation(); state.selectedLogin=btn.getAttribute('data-login'); renderTable(); renderProfile()}))}
function applyFilters(){const q=els.searchText.value.trim().toLowerCase(), minScore=Number(els.minScore.value||0), availabilityMode=els.availabilityOnly.value, contactMode=els.contactOnly.value, activeKeyword=state.activeKeyword; let rows=state.raw.filter(r=>{if(r.score<minScore) return false; if(q&&!includesText(r,q)) return false; if(availabilityMode==='yes'&&!r.availability_signal) return false; if(availabilityMode==='no'&&r.availability_signal) return false; if(contactMode==='yes'&&!r.has_public_contact) return false; if(contactMode==='no'&&r.has_public_contact) return false; if(activeKeyword&&!splitKeywords(r.matching_keywords).map(x=>x.toLowerCase()).includes(activeKeyword.toLowerCase())) return false; return true}); rows.sort((a,b)=>b.score-a.score); state.filtered=rows; if(!state.selectedLogin&&rows.length) state.selectedLogin=rows[0].login; if(state.selectedLogin&&!rows.some(r=>r.login===state.selectedLogin)) state.selectedLogin=rows.length?rows[0].login:null; renderMetrics(); renderKeywordChips(); renderBars(els.keywordBars,getCounts(state.filtered,'matching_keywords')); renderBars(els.locationBars,getCounts(state.filtered,'location')); renderTable(); renderProfile()}
function setData(rows){state.raw=rows||[]; state.filtered=[...state.raw]; state.selectedLogin=state.raw.length?state.raw[0].login:null; applyFilters()}
async function parseJobDescription(){const jd=els.jobDescription.value.trim(); if(!jd) throw new Error('Paste a job description first.'); const res=await fetch('/api/parse-job-description',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({job_description:jd,role_hint:els.roleHint.value})}); const data=await res.json(); if(!res.ok) throw new Error(data.error||'JD parsing failed'); state.parsedGroups=data.groups||{}; renderParsedGroups(state.parsedGroups); els.stacks.value=(data.stack_terms||[]).join(','); els.keywords.value=(data.scoring_keywords||[]).join(','); return data}
async function runSearchApi(){const payload={phrase:els.phrase.value,location:els.location.value,stacks:els.stacks.value,keywords:els.keywords.value,extra_query:els.extraQuery.value,per_query_limit:Number(els.perQueryLimit.value||30),pages:Number(els.pages.value||1),max_enrich:Number(els.maxEnrich.value||50),min_score:Number(els.minScoreServer.value||0),use_defaults:false}; const res=await fetch('/api/run-search',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)}); const data=await res.json(); if(!res.ok) throw new Error(data.error||'Search failed'); setData(data.candidates||[]); return data}
async function parseAndSearch(){els.parseAndSearch.disabled=true; els.runSearchOnly.disabled=true; els.runStatus.textContent='Parsing job description...'; try{const parsed=await parseJobDescription(); els.runStatus.textContent=`Parsed JD. Role: ${parsed.role||'n/a'}. Searching candidates...`; const result=await runSearchApi(); els.runStatus.textContent=`Completed. Parsed ${parsed.scoring_keywords.length} skills and returned ${result.candidates.length} candidates.`}catch(err){els.runStatus.textContent=`Error: ${err.message}`}finally{els.parseAndSearch.disabled=false; els.runSearchOnly.disabled=false}}
async function runSearchOnly(){els.runSearchOnly.disabled=true; els.parseAndSearch.disabled=true; els.runStatus.textContent='Running GitHub search...'; try{const result=await runSearchApi(); els.runStatus.textContent=`Completed. Returned ${result.candidates.length} candidates.`}catch(err){els.runStatus.textContent=`Error: ${err.message}`}finally{els.runSearchOnly.disabled=false; els.parseAndSearch.disabled=false}}
els.parseAndSearch.addEventListener('click',parseAndSearch); els.runSearchOnly.addEventListener('click',runSearchOnly); els.exportCsv.addEventListener('click',()=>window.open('/api/export-last-search','_blank')); [els.searchText,els.minScore,els.availabilityOnly,els.contactOnly].forEach(el=>{el.addEventListener('input',applyFilters); el.addEventListener('change',applyFilters)}); els.minScore.addEventListener('input',()=>els.minScoreValue.textContent=els.minScore.value); renderParsedGroups({}); setData([]);
</script></body></html>"""

def get_token(): return os.getenv("GITHUB_TOKEN", "").strip()
def get_openai_client():
    if OpenAI is None: return None
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key: return None
    base_url = os.getenv("OPENAI_BASE_URL", "").strip() or None
    return OpenAI(api_key=api_key, base_url=base_url) if base_url else OpenAI(api_key=api_key)
def get_headers(token, accept="application/vnd.github+json"): return {"Authorization": f"Bearer {token}", "Accept": accept, "User-Agent": "devready-github-dashboard"}
def handle_rate_limit(resp):
    if resp.status_code not in (403, 429): return
    remaining = resp.headers.get("X-RateLimit-Remaining"); reset = resp.headers.get("X-RateLimit-Reset")
    if remaining == "0" and reset: time.sleep(max(1, int(reset) - int(time.time()) + 1)); return
    resp.raise_for_status()
def rest_get(url, token, params=None, accept="application/vnd.github+json"):
    resp = requests.get(url, headers=get_headers(token, accept=accept), params=params, timeout=30)
    handle_rate_limit(resp); resp.raise_for_status(); return resp.json()
def graphql_post(query, variables, token):
    resp = requests.post(GRAPHQL_URL, headers=get_headers(token), json={"query": query, "variables": variables}, timeout=30)
    handle_rate_limit(resp); resp.raise_for_status(); payload = resp.json()
    if "errors" in payload: raise RuntimeError(f"GraphQL error: {payload['errors']}")
    return payload["data"]
GRAPHQL_USER_QUERY = '''query($login: String!) { user(login: $login) { login name bio location company websiteUrl url followers { totalCount } repositories(privacy: PUBLIC) { totalCount } pinnedItems(first: 6, types: REPOSITORY) { nodes { ... on Repository { name primaryLanguage { name } } } } recentRepositories: repositories(first: 12, privacy: PUBLIC, ownerAffiliations: OWNER, orderBy: {field: UPDATED_AT, direction: DESC}) { nodes { name primaryLanguage { name } } } } }'''
def unique_preserve_order(items):
    seen=set(); out=[]
    for item in items:
        low=item.lower()
        if low not in seen: seen.add(low); out.append(item)
    return out
def normalize_space(text): return re.sub(r"\s+", " ", text or "").strip()
def detect_role(text, role_hint):
    if role_hint and role_hint.lower() != "auto": return role_hint.lower()
    scores = {role: sum(1 for hint in hints if hint in text) for role, hints in ROLE_HINTS.items()}
    return max(scores, key=scores.get) if scores else "frontend"
def heuristic_parse_job_description(job_description, role_hint="auto"):
    jd = normalize_space(job_description)
    if not jd: raise ValueError("Job description is empty.")
    low = jd.lower(); role = detect_role(low, role_hint); found=[]
    for canonical, variants in SKILL_SYNONYMS.items():
        if any(v in low for v in variants): found.append(canonical)
    found.extend(ROLE_HINTS.get(role, [])); found = unique_preserve_order(found); groups={}
    for group_name, skills in SKILL_GROUPS.items():
        hits=[s for s in skills if s in found]
        if hits: groups[group_name]=unique_preserve_order(hits)
    ordered=[]
    for bucket in ("frontend_frameworks","languages","styling_ui","data_api","testing","platform"): ordered.extend(groups.get(bucket, []))
    if role not in ordered: ordered.insert(0, role)
    return {"role": role, "groups": groups, "stack_terms": unique_preserve_order([s for s in ordered if s])[:10], "scoring_keywords": unique_preserve_order(found)[:18], "source": "heuristic"}
def ai_parse_job_description(job_description, role_hint="auto"):
    client = get_openai_client()
    if client is None: return heuristic_parse_job_description(job_description, role_hint)
    model = os.getenv("OPENAI_MODEL", "").strip() or "gpt-4.1-mini"
    prompt = f"""Extract a concise structured hiring profile from this job description. Return strict JSON with keys: role, stack_terms, scoring_keywords, groups. groups must be an object with arrays for likely categories like languages, frontend_frameworks, styling_ui, data_api, testing, platform. stack_terms max 10. scoring_keywords max 18. Normalize names like react, typescript, next.js, graphql, rest, tailwind, material ui. Role hint: {role_hint}\n\nJob description:\n{job_description}"""
    resp = client.responses.create(model=model, input=prompt)
    text = getattr(resp, "output_text", "") or ""
    try:
        data = json.loads(text); data["source"] = "openai"; return data
    except Exception:
        return heuristic_parse_job_description(job_description, role_hint)
def init_db():
    if psycopg is None: return
    db_url = os.getenv("DATABASE_URL", "").strip()
    if not db_url: return
    with psycopg.connect(db_url) as conn:
        with conn.cursor() as cur:
            cur.execute("create table if not exists jd_profiles (id bigserial primary key, created_at timestamptz default now(), role text, job_description text, parsed_profile jsonb)")
            cur.execute("create table if not exists candidate_results (id bigserial primary key, created_at timestamptz default now(), jd_profile_id bigint, github_login text, candidate_json jsonb)")
        conn.commit()
def store_jd_profile(job_description, parsed_profile):
    if psycopg is None: return None
    db_url = os.getenv("DATABASE_URL", "").strip()
    if not db_url: return None
    with psycopg.connect(db_url) as conn:
        with conn.cursor() as cur:
            cur.execute("insert into jd_profiles (role, job_description, parsed_profile) values (%s, %s, %s) returning id", (parsed_profile.get("role"), job_description, json.dumps(parsed_profile)))
            row = cur.fetchone()
        conn.commit()
    return int(row[0]) if row else None
def store_candidate_rows(jd_profile_id, rows):
    if psycopg is None or jd_profile_id is None: return
    db_url = os.getenv("DATABASE_URL", "").strip()
    if not db_url: return
    with psycopg.connect(db_url) as conn:
        with conn.cursor() as cur:
            for row in rows:
                cur.execute("insert into candidate_results (jd_profile_id, github_login, candidate_json) values (%s, %s, %s)", (jd_profile_id, row.get("login"), json.dumps(row)))
        conn.commit()
def get_profile_readme(token, login):
    try:
        data = rest_get(f"{REST_BASE}/repos/{login}/{login}/readme", token); content = data.get("content", "")
        if not content: return ""
        return base64.b64decode(content).decode("utf-8", errors="ignore")[:5000]
    except Exception: return ""
def first_public_email(text):
    if not text: return ""
    m = EMAIL_REGEX.search(text)
    if not m: return ""
    email = m.group(1)
    return "" if "noreply" in email.lower() else email
def first_linkedin(text):
    if not text: return ""
    m = LINKEDIN_REGEX.search(text)
    return m.group(1) if m else ""
@dataclass
class Candidate:
    login: str; name: str = ""; bio: str = ""; location: str = ""; company: str = ""; website_url: str = ""; followers: int = 0; public_repos: int = 0; pinned_repo_names: str = ""; top_languages: str = ""; recent_repo_names: str = ""; recent_repo_count: int = 0; matching_keywords: str = ""; availability_signal: bool = False; score: int = 0; profile_url: str = ""; notes: str = ""; profile_readme: str = ""; public_email: str = ""; linkedin_url: str = ""; contact_paths: str = ""; best_contact_method: str = ""; has_public_contact: bool = False
def build_contact_fields(candidate):
    text = " ".join([candidate.bio, candidate.profile_readme, candidate.website_url]); public_email = first_public_email(text); linkedin = first_linkedin(text); contact_paths=[]; best=""
    if candidate.website_url: contact_paths.append("website"); best="Website / contact form"
    if linkedin: contact_paths.append("linkedin"); best = best or "LinkedIn"
    if public_email: contact_paths.append("public_email"); best = best or "Public email"
    if not best and candidate.profile_url: best = "GitHub profile only"
    candidate.public_email=public_email; candidate.linkedin_url=linkedin; candidate.contact_paths=", ".join(contact_paths); candidate.best_contact_method=best; candidate.has_public_contact=bool(candidate.website_url or linkedin or public_email)
    return candidate
def search_users(token, query, per_page=30, max_pages=1):
    logins=[]; seen=set()
    for page in range(1, max_pages+1):
        data = rest_get(f"{REST_BASE}/search/users", token, params={"q": query, "per_page": per_page, "page": page})
        for item in data.get("items", []):
            login = item.get("login")
            if login and login not in seen: seen.add(login); logins.append(login)
        if len(data.get("items", [])) < per_page: break
    return logins
def enrich_user(token, login):
    data = graphql_post(GRAPHQL_USER_QUERY, {"login": login}, token); user = data.get("user")
    if not user: return Candidate(login=login, notes="User not found")
    pinned_names=[]; recent_names=[]; langs=[]
    for repo in user.get("pinnedItems", {}).get("nodes", []) or []:
        if repo:
            pinned_names.append(repo.get("name", "")); lang=((repo.get("primaryLanguage") or {}).get("name") or "").strip();
            if lang: langs.append(lang)
    for repo in user.get("recentRepositories", {}).get("nodes", []) or []:
        if repo:
            recent_names.append(repo.get("name", "")); lang=((repo.get("primaryLanguage") or {}).get("name") or "").strip();
            if lang: langs.append(lang)
    c = Candidate(login=user.get("login") or login, name=user.get("name") or "", bio=user.get("bio") or "", location=user.get("location") or "", company=user.get("company") or "", website_url=user.get("websiteUrl") or "", followers=int((user.get("followers") or {}).get("totalCount") or 0), public_repos=int((user.get("repositories") or {}).get("totalCount") or 0), pinned_repo_names=", ".join([x for x in pinned_names if x]), top_languages=", ".join(unique_preserve_order([x for x in langs if x])[:8]), recent_repo_names=", ".join([x for x in recent_names[:8] if x]), recent_repo_count=len([x for x in recent_names if x]), profile_url=user.get("url") or "", profile_readme=get_profile_readme(token, login))
    return build_contact_fields(c)
def build_query_from_parts(phrase="", location="", stacks="", extra=""):
    parts=[]
    if phrase:
        phrase=phrase.strip(); parts.append(phrase if "in:bio" in phrase else f'"{phrase}" in:bio')
    if location: parts.append(f"location:{location.strip()}")
    stack_terms=[s.strip() for s in str(stacks).split(",") if s.strip()]
    if stack_terms: parts.append("(" + " OR ".join(stack_terms) + ")")
    if extra: parts.append(extra.strip())
    return " ".join(parts).strip()
def parse_target_keywords(raw): return [x.strip() for x in raw.split(",") if x.strip()] if raw else []
def extract_matching_keywords(text, repo_text):
    haystack = f"{text} {repo_text}".lower(); found=[]
    for canonical, variants in SKILL_SYNONYMS.items():
        if any(v in haystack for v in variants): found.append(canonical)
    return unique_preserve_order(found)
def has_availability_signal(text):
    low=(text or "").lower(); return any(re.search(pattern, low) for pattern in AVAILABILITY_PATTERNS)
def score_candidate(candidate, target_keywords, stack_terms):
    text = " ".join([candidate.name,candidate.bio,candidate.company,candidate.location,candidate.top_languages,candidate.profile_readme]); repo_text = candidate.recent_repo_names + " " + candidate.pinned_repo_names; detected = extract_matching_keywords(text, repo_text); score=0; notes=[]
    availability = has_availability_signal(candidate.bio + " " + candidate.profile_readme)
    if availability: score += 40; notes.append("explicit availability signal")
    combined=(text + " " + repo_text).lower(); keyword_hits=sum(1 for kw in target_keywords if kw.lower() in combined); stack_hits=sum(1 for st in stack_terms if st.lower() in combined)
    if keyword_hits: score += min(20, keyword_hits*5); notes.append(f"{keyword_hits} target keyword hit(s)")
    if stack_hits: score += min(20, stack_hits*4); notes.append(f"{stack_hits} stack term hit(s)")
    if detected: score += min(15, len(detected)*2); notes.append("stack match")
    if candidate.recent_repo_count >= 6: score += 15; notes.append("recent repo activity")
    elif candidate.recent_repo_count >= 3: score += 8; notes.append("some recent activity")
    if candidate.has_public_contact: score += 5; notes.append("public contact path present")
    if candidate.website_url: score += 5; notes.append("website/portfolio present")
    if candidate.followers >= 100: score += 5; notes.append("higher follower count")
    elif candidate.followers >= 25: score += 2
    if candidate.public_repos >= 20: score += 5; notes.append("substantial public repos")
    candidate.matching_keywords=", ".join(detected); candidate.availability_signal=availability; candidate.score=score; candidate.notes="; ".join(notes); return candidate
LAST_RESULTS=[]; LAST_QUERY_SUMMARY=""
def dedupe_logins(items):
    seen=set(); out=[]
    for item in items:
        low=item.lower()
        if low not in seen: seen.add(low); out.append(item)
    return out
def run_miner(phrase="", location="", stacks="", keywords="", extra_query="", per_query_limit=30, pages=1, max_enrich=50, min_score=0, use_defaults=False):
    token=get_token()
    if not token: raise RuntimeError("Missing GITHUB_TOKEN environment variable.")
    queries=[]; built_query=build_query_from_parts(phrase=phrase, location=location, stacks=stacks, extra=extra_query)
    if built_query: queries.append(built_query)
    if use_defaults: queries.extend(DEFAULT_QUERIES)
    if not queries: queries=['"open to work" in:bio']
    target_keywords=parse_target_keywords(keywords); stack_terms=parse_target_keywords(stacks); logins=[]
    for q in queries:
        try: logins.extend(search_users(token, q, per_page=per_query_limit, max_pages=pages))
        except Exception: continue
    candidates=[]
    for login in dedupe_logins(logins)[:max_enrich]:
        try:
            c=enrich_user(token, login); c=score_candidate(c, target_keywords, stack_terms)
            if c.score >= min_score: candidates.append(c)
        except Exception: continue
    candidates.sort(key=lambda x: x.score, reverse=True)
    return {"queries": queries, "candidates": [asdict(c) for c in candidates]}
@app.route("/")
def index(): return render_template_string(HTML)
@app.route("/api/parse-job-description", methods=["POST"])
def api_parse_job_description():
    payload=request.get_json(silent=True) or {}; jd=str(payload.get("job_description", "")); role_hint=str(payload.get("role_hint", "auto")); parsed=ai_parse_job_description(jd, role_hint); jd_id=store_jd_profile(jd, parsed); parsed["jd_profile_id"]=jd_id; return jsonify(parsed)
@app.route("/api/run-search", methods=["POST"])
def api_run_search():
    global LAST_RESULTS, LAST_QUERY_SUMMARY
    payload=request.get_json(silent=True) or {}
    result=run_miner(phrase=str(payload.get("phrase", "")), location=str(payload.get("location", "")), stacks=str(payload.get("stacks", "")), keywords=str(payload.get("keywords", "")), extra_query=str(payload.get("extra_query", "")), per_query_limit=max(1,min(100,int(payload.get("per_query_limit",30)))), pages=max(1,min(10,int(payload.get("pages",1)))), max_enrich=max(1,min(200,int(payload.get("max_enrich",50)))), min_score=max(0,min(100,int(payload.get("min_score",0)))), use_defaults=bool(payload.get("use_defaults", False)))
    LAST_RESULTS=result["candidates"]; LAST_QUERY_SUMMARY=" | ".join(result["queries"]); store_candidate_rows(payload.get("jd_profile_id"), LAST_RESULTS)
    return jsonify({"query_summary": LAST_QUERY_SUMMARY, "candidates": LAST_RESULTS})
@app.route("/api/export-last-search")
def api_export_last_search():
    if not LAST_RESULTS: return jsonify({"error": "No results available yet. Run a search first."}), 400
    output=io.StringIO(); writer=csv.DictWriter(output, fieldnames=list(LAST_RESULTS[0].keys())); writer.writeheader(); [writer.writerow(r) for r in LAST_RESULTS]
    return Response(output.getvalue().encode("utf-8"), mimetype="text/csv", headers={"Content-Disposition": "attachment; filename=devready_candidates.csv"})
if __name__ == "__main__":
    init_db(); token=get_token()
    if not token:
        print("ERROR: GITHUB_TOKEN is not set."); print('$env:GITHUB_TOKEN="your_new_token_here"'); print("Then run:"); print("python app.py"); raise SystemExit(1)
    app.run(host="127.0.0.1", port=5000, debug=False)
