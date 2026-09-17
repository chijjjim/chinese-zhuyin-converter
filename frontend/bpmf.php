<!DOCTYPE html>
<html lang="zh-Hant">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>國字轉注音</title>
    <link rel="icon" href="data:,">
    <link rel="stylesheet" href="bpmf.css">
</head>
<body>

<div class="title">
    <h1>國字轉注音</h1>

    <div class="upload">
        <label for="fileInput" class="upload-btn">上傳 TXT 檔案</label>
        <input type="file" id="fileInput" accept=".txt">
        <p id="fileName">尚未選擇檔案</p>
    </div>

    <div class="text">
        <h2>檔案內容</h2>
        <textarea id="filetext" placeholder="請輸入或貼上要轉換的中文文字..."></textarea>
    </div>

    <!-- 點字選項 -->
    <div class="braille-option">
        <label class="checkbox-label">
            <input type="checkbox" id="includeBraille">
            <span>顯示點字</span>
        </label>
    </div>

    <!-- 載入動畫 -->
    <div class="loading" id="loading">轉換中，請稍候...</div>

    <!-- 錯誤訊息 -->
    <div class="error-message" id="errorMessage"></div>

    <button id="tobpmf">轉換成注音</button>

    <div class="bpmf-section">
        <h2>轉換結果</h2>
        <div id="bpmfLine" class="bpmf-line"></div>
        <button class="download-btn" id="downloadbtn">下載</button>
    </div>
</div>

<script>
// ==========================================
// API 設定
// ==========================================
const API_BASE_URL = '/bpmf/api';

// ==========================================
// DOM 元素
// ==========================================
const fileInput = document.getElementById('fileInput');
const fileName = document.getElementById('fileName');
const filetext = document.getElementById('filetext');
const tobpmf = document.getElementById('tobpmf');
const bpmfLine = document.getElementById('bpmfLine');
const downloadbtn = document.getElementById('downloadbtn');
const loading = document.getElementById('loading');
const errorMessage = document.getElementById('errorMessage');
const includeBrailleCheckbox = document.getElementById('includeBraille');

// 儲存轉換結果（用於下載）
let currentResults = [];
let includeBraille = false;

// ==========================================
// 檔案上傳處理
// ==========================================
fileInput.addEventListener('change', function() {
    const file = fileInput.files[0];
    if (!file) return;

    fileName.textContent = file.name;

    const reader = new FileReader();
    reader.onload = function(){
        filetext.value = reader.result;
    };
    reader.readAsText(file, 'utf-8');
});

// ==========================================
// 轉換成注音（呼叫後端 API）
// ==========================================
tobpmf.addEventListener('click', async function() {
    bpmfLine.innerHTML = '';
    const text = filetext.value.trim();
    includeBraille = includeBrailleCheckbox.checked;

    if (!text) {
        showError('請輸入要轉換的文字！');
        return;
    }

    // 顯示載入動畫
    showLoading();
    hideError();

    try {
        // 呼叫後端 API
        const response = await fetch(`${API_BASE_URL}/convert`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                text: text,
                include_braille: includeBraille
            })
        });

        if (!response.ok) {
            throw new Error(`HTTP 錯誤！狀態: ${response.status}`);
        }

        const data = await response.json();

        // 檢查回應
        if (!data.success) {
            throw new Error(data.error_message || '轉換失敗');
        }

        // 儲存結果
        currentResults = data.results;

        // 顯示結果
        displayResults(data.results, includeBraille);

    } catch (error) {
        showError(`轉換失敗：${error.message}`);
        bpmfLine.innerHTML = '<p style="color: red;">轉換失敗，請檢查後端伺服器是否運行</p>';
    } finally {
        hideLoading();
    }
});

// ==========================================
// 建立單一字元單位
// ==========================================
function createCharUnit(item, showBraille, index) {
    // 建立字元單位
    const unit = document.createElement('span');
    unit.className = 'char-unit';
    unit.dataset.index = index;

    // 取得字元類型
    const charType = item.char_type || 'chinese';

    // 加入類型標記
    unit.classList.add(`char-type-${charType}`);

    // 漢字/字元顯示
    const hanzi = document.createElement('span');
    hanzi.className = 'hanzi';

    // 如果是中文多音字，標記為紅色
    if (charType === 'chinese' && item.is_polyphone) {
        hanzi.classList.add('polyphone');
    }

    hanzi.textContent = item.character;

    // 中文字點擊開新分頁連到教育部辭典
    if (charType === 'chinese') {
        hanzi.addEventListener('click', () => {
            const dictUrl = `https://dict.revised.moe.edu.tw/search.jsp?la=0&powerMode=0&word=${encodeURIComponent(item.character)}`;
            window.open(dictUrl, '_blank');
        });
    }

    // 注音（只有中文才顯示）
    const bpmf = document.createElement('span');
    bpmf.className = 'bpmf';

    if (charType === 'chinese') {
        bpmf.textContent = item.primary_zhuyin;

        // 如果是多音字且有多個選項，建立下拉選單
        if (item.is_polyphone && item.all_zhuyin_options && item.all_zhuyin_options.length > 1) {
            bpmf.classList.add('clickable');

            const select = document.createElement('select');
            select.className = 'bpmf-select';

            item.all_zhuyin_options.forEach(opt => {
                const o = document.createElement('option');
                o.value = opt;
                o.textContent = opt;
                if (opt === item.primary_zhuyin) {
                    o.selected = true;
                }
                select.appendChild(o);
            });

            // 點擊注音顯示下拉選單
            bpmf.addEventListener('click', (e) => {
                e.stopPropagation();
                // 隱藏其他所有下拉選單
                document.querySelectorAll('.bpmf-select').forEach(s => {
                    s.style.display = 'none';
                });
                select.style.display = 'block';
            });

            // 選擇注音後更新點字
            select.addEventListener('change', async () => {
                const newZhuyin = select.value;
                bpmf.textContent = newZhuyin;
                select.style.display = 'none';

                // 更新 currentResults 中的資料
                item.primary_zhuyin = newZhuyin;

                // 如果有點字模式，呼叫 API 更新點字
                if (includeBraille) {
                    try {
                        const response = await fetch(`${API_BASE_URL}/braille`, {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ zhuyin: newZhuyin })
                        });
                        const data = await response.json();

                        if (data.success && data.braille) {
                            item.braille = data.braille;
                            item.braille_count = data.braille_count;

                            // 重新計算換行並顯示
                            displayResults(currentResults, true);
                        }
                    } catch (error) {
                        // 更新點字失敗時靜默處理
                    }
                }
            });

            unit.appendChild(select);
        }
    } else {
        // 非中文：不顯示注音（或顯示類型標籤）
        bpmf.textContent = '';
        bpmf.classList.add('no-zhuyin');
    }

    // 組合元素（國字在上、注音在中、點字在下）
    unit.appendChild(hanzi);
    unit.appendChild(bpmf);

    // 如果有點字，加入點字顯示
    if (showBraille && item.braille) {
        const braille = document.createElement('span');
        braille.className = 'braille';
        braille.textContent = item.braille.symbols;
        braille.title = `e_value: ${item.braille.e_value}`;
        unit.appendChild(braille);
    }

    return unit;
}

// ==========================================
// 顯示轉換結果
// ==========================================
function displayResults(results, showBraille) {
    bpmfLine.innerHTML = '';

    if (!showBraille) {
        // 非點字模式：使用原本的 CSS Grid（15字一行）
        bpmfLine.classList.remove('braille-mode');

        results.forEach((item, index) => {
            const unit = createCharUnit(item, false, index);
            bpmfLine.appendChild(unit);
        });

        return;
    }

    // 點字模式：40 點字符號換行
    bpmfLine.classList.add('braille-mode');

    const MAX_BRAILLE_PER_LINE = 40;
    let currentRow = document.createElement('div');
    currentRow.className = 'braille-row';
    let currentBrailleCount = 0;

    results.forEach((item, index) => {
        const charBrailleCount = item.braille ? item.braille.symbols.length : 0;

        // 如果加入這個字會超過 40，就換行（但如果當前行是空的，則強制放入）
        if (currentBrailleCount + charBrailleCount > MAX_BRAILLE_PER_LINE && currentBrailleCount > 0) {
            // 這一行已滿，加上 full-row class 讓它撐滿寬度
            currentRow.classList.add('full-row');
            bpmfLine.appendChild(currentRow);
            currentRow = document.createElement('div');
            currentRow.className = 'braille-row';
            currentBrailleCount = 0;
        }

        const unit = createCharUnit(item, true, index);
        currentRow.appendChild(unit);
        currentBrailleCount += charBrailleCount;
    });

    // 加入最後一行（未滿的行不加 full-row class，維持靠左排列）
    if (currentRow.children.length > 0) {
        bpmfLine.appendChild(currentRow);
    }

    // 點擊其他地方隱藏下拉選單
    document.addEventListener('click', (e) => {
        if (!e.target.closest('.char-unit')) {
            document.querySelectorAll('.bpmf-select').forEach(s => {
                s.style.display = 'none';
            });
        }
    });
}

// ==========================================
// 下載結果
// ==========================================
downloadbtn.addEventListener('click', () => {
    if (currentResults.length === 0) {
        showError('目前無檔案可以下載');
        return;
    }

    let content = '';

    if (includeBraille) {
        // 下載格式：國字 注音 e_value
        currentResults.forEach(item => {
            const zhuyin = item.primary_zhuyin || '';
            const eValue = item.braille ? item.braille.e_value : '';
            content += `${item.character} ${zhuyin} ${eValue}\n`;
        });
    } else {
        // 原本的下載格式：只有注音（中文才有）
        const bpmfArray = currentResults
            .filter(item => item.char_type === 'chinese')
            .map(item => item.primary_zhuyin);
        content = bpmfArray.join(' ');
    }

    const blob = new Blob([content], {
        type: 'text/plain;charset=utf-8;'
    });

    const url = URL.createObjectURL(blob);

    const a = document.createElement('a');
    a.href = url;
    a.download = includeBraille ? 'braille_result.txt' : 'bpmf_result.txt';
    document.body.appendChild(a);
    a.click();

    document.body.removeChild(a);
    URL.revokeObjectURL(url);
});

// ==========================================
// 輔助函式
// ==========================================
function showLoading() {
    loading.style.display = 'block';
    tobpmf.disabled = true;
}

function hideLoading() {
    loading.style.display = 'none';
    tobpmf.disabled = false;
}

function showError(message) {
    errorMessage.textContent = message;
    errorMessage.style.display = 'block';
    setTimeout(() => {
        hideError();
    }, 5000);
}

function hideError() {
    errorMessage.style.display = 'none';
}

// ==========================================
// 測試 API 連線
// ==========================================
async function testAPIConnection() {
    try {
        const response = await fetch(`${API_BASE_URL}/health`);
        // 連線測試靜默執行
    } catch (error) {
        // 連線失敗時靜默處理
    }
}

// 頁面載入時測試連線
testAPIConnection();
</script>

</body>
</html>
