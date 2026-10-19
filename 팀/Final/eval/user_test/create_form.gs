/**
 * AI Promise 사용자 테스트 설문을 구글 설문지로 한 번에 만듭니다.
 *
 * 기준 문서: 공통 폴더 '1015_AI_Promise_사용자테스트_설문지_최종'
 * 순서는 기록지(1015_AI_Promise_사용자테스트_기록지_최종)의 설문1~설문6 칸과 같습니다.
 *
 * 쓰는 방법 (약 2분, 한 번만)
 *   1. script.google.com 접속 > 새 프로젝트
 *   2. 기본 코드를 지우고 이 파일 전체를 붙여 넣은 뒤 저장
 *   3. 위쪽 함수 목록에서 createSurvey 선택 > 실행
 *   4. 권한 요청이 나오면 본인 계정 선택 > 고급 > 프로젝트로 이동 > 허용
 *   5. 아래 '실행 로그'에 나온 참가자용 링크를 진행자(김서원, 서준용)에게 전달
 *
 * 지키는 것
 *   - 이름, 연락처, 이메일은 받지 않습니다. (이메일 수집 끔, 로그인 요구 끔)
 *   - 편집 링크와 응답 시트는 팀 안에서만 씁니다. 참가자에게는 응답 링크만 보냅니다.
 *   - 두 번 실행해도 설문이 두 개 생기지 않도록, 같은 이름의 설문이 공통 폴더에 있으면 멈춥니다.
 */

const FOLDER_ID = '1h_eXpFg-VOCYxygZxR8r8Ssfm3c_EgIW'; // 드라이브 '공통' 폴더
const FORM_FILE_NAME = '1015_AI_Promise_사용자테스트_설문(구글설문)';
const SHEET_FILE_NAME = '1015_AI_Promise_사용자테스트_설문응답';

function createSurvey() {
  const folder = DriveApp.getFolderById(FOLDER_ID);
  const existing = folder.getFilesByName(FORM_FILE_NAME);
  if (existing.hasNext()) {
    const old = existing.next();
    Logger.log('이미 만든 설문이 있어서 멈춥니다: ' + old.getUrl());
    Logger.log('다시 만들려면 공통 폴더에서 그 설문 파일 이름을 바꾼 뒤 실행하세요.');
    return;
  }

  // 1) 설문 만들기와 설정
  const form = FormApp.create(FORM_FILE_NAME);
  form.setTitle('AI Promise 사용자 테스트 설문');
  form.setDescription(
    '안녕하세요. 이 설문은 수업 Final Project로 개발한 ‘AI Promise’의 사용성을 확인하기 위한 약 2분 설문입니다. ' +
    '이름·연락처·이메일은 수집하지 않습니다. ' +
    '응답은 서비스 개선과 프로젝트 결과보고서·발표에 집계 형태로 사용됩니다. ' +
    '자유응답은 익명으로 인용될 수 있습니다. ' +
    '참여를 원하지 않으면 언제든 중단할 수 있습니다.'
  );
  safe_('이메일 수집 끔', function () { form.setCollectEmail(false); });
  safe_('로그인 요구 끔', function () { form.setRequireLogin(false); });
  safe_('응답 1회 제한 끔', function () { form.setLimitOneResponsePerUser(false); });
  safe_('응답 수정 허용 끔', function () { form.setAllowResponseEdits(false); });
  safe_('다른 응답 제출 링크 끔', function () { form.setShowLinkToRespondAgain(false); });
  safe_('진행률 표시 끔', function () { form.setProgressBar(false); });
  safe_('질문 순서 섞기 끔', function () { form.setShuffleQuestions(false); });
  safe_('퀴즈 끔', function () { form.setIsQuiz(false); });
  form.setConfirmationMessage('참여해 주셔서 감사합니다. 응답은 AI Promise 개선과 Final Project 결과 정리에만 사용됩니다.');

  // 2) 시작: 동의와 참가자 번호
  form.addCheckboxItem()
    .setTitle('참여 동의')
    .setHelpText('위 안내를 읽었고 설문 참여에 동의하시면 체크해 주세요. 동의하지 않으시면 창을 닫으시면 됩니다.')
    .setChoiceValues(['동의합니다'])
    .setRequired(true);

  const idRule = FormApp.createTextValidation()
    .setHelpText('P01처럼 P와 숫자 2자리로 적어 주세요. 의견 참여는 의견01, 예행연습은 R0입니다.')
    .requireTextMatchesPattern('^(R0|P[0-9]{2}|의견[0-9]{1,2})$')
    .build();
  form.addTextItem()
    .setTitle('참가자 번호')
    .setHelpText('진행자에게 받은 참가자 번호를 입력해 주세요. (예: P01) 비실시간 의견 참여자는 ‘의견01’처럼 입력합니다.')
    .setValidation(idRule)
    .setRequired(true);

  // 3) 설문 1~6 (기록지 설문1~설문6과 같은 번호)
  form.addSectionHeaderItem()
    .setTitle('사용 소감')
    .setHelpText('1~4번은 꼭 답해 주시고, 5~6번은 원하실 때만 답해 주세요.');

  form.addScaleItem()
    .setTitle('1. AI Promise에서 제시한 판정 이유와 공시 근거를 이해하기 쉬웠나요?')
    .setBounds(1, 5)
    .setLabels('전혀 이해하기 어려웠다', '매우 이해하기 쉬웠다')
    .setRequired(true);

  form.addScaleItem()
    .setTitle('2. AI Promise의 결과를 얼마나 믿고 참고할 수 있다고 느꼈나요?')
    .setBounds(1, 5)
    .setLabels('전혀 신뢰하기 어렵다', '매우 신뢰할 수 있다')
    .setRequired(true);

  form.addScaleItem()
    .setTitle('3. 실제 취업·이직 면접 준비에서 AI Promise를 사용하고 싶나요?')
    .setBounds(1, 5)
    .setLabels('전혀 사용하고 싶지 않다', '매우 사용하고 싶다')
    .setRequired(true);

  form.addParagraphTextItem()
    .setTitle('4. 사용하면서 헷갈렸거나 고치면 좋겠다고 느낀 점을 자유롭게 적어 주세요.')
    .setRequired(true);

  form.addMultipleChoiceItem()
    .setTitle('5. 가장 도움이 된 기능은 무엇이었나요?')
    .setChoiceValues(['회사의 AI 약속 목록', '약속과 후속 실행 근거 비교', '판정 이유', 'DART 원문 링크', '면접 카드', '아직 잘 모르겠다'])
    .showOtherOption(true)
    .setRequired(false);

  form.addParagraphTextItem()
    .setTitle('6. 이 서비스를 한 문장으로 평가한다면 어떻게 표현하시겠어요?')
    .setRequired(false);

  // 4) 응답 시트 연결, 공통 폴더로 옮기기, 응답 받기 켜기
  const sheet = SpreadsheetApp.create(SHEET_FILE_NAME);
  form.setDestination(FormApp.DestinationType.SPREADSHEET, sheet.getId());
  DriveApp.getFileById(form.getId()).moveTo(folder);
  DriveApp.getFileById(sheet.getId()).moveTo(folder);
  safe_('설문 게시', function () { form.setPublished(true); });
  form.setAcceptingResponses(true);

  // 5) 링크 알려 주기
  const respondUrl = form.getPublishedUrl();
  let shortUrl = respondUrl;
  safe_('짧은 링크', function () { shortUrl = form.shortenFormUrl(respondUrl); });
  Logger.log('참가자용 응답 링크 (진행자에게 전달): ' + shortUrl);
  Logger.log('편집 링크 (팀 안에서만): ' + form.getEditUrl());
  Logger.log('응답 시트 (팀 안에서만): ' + sheet.getUrl());
  Logger.log('문항 수: ' + form.getItems().length + ' (동의, 번호, 소감 제목, 설문 1~6 = 9)');
}

const SERVICE_URL = 'https://ai-promise-six.vercel.app';
const SELF_TEST_HEADER = '작은 과제 (약 3분)';

// updateSurvey가 넣는 문항 6개. 순서대로 '참가자 번호' 바로 뒤(3번째 자리부터)에 놓입니다.
const SELF_TEST_ITEMS = [
  {
    title: '지금 상황에 가장 가까운 것을 골라 주세요.',
    add: function (form, title) {
      return form.addMultipleChoiceItem()
        .setTitle(title)
        .setChoiceValues(['취업 준비 중', '이직 준비 중', '재직 중 (이직 생각은 없음)', '학생 (아직 취업 준비 전)'])
        .showOtherOption(true)
        .setRequired(true);
    },
  },
  {
    title: SELF_TEST_HEADER,
    add: function (form, title) {
      return form.addSectionHeaderItem()
        .setTitle(title)
        .setHelpText('서비스 주소(' + SERVICE_URL + ')에서 기업 1곳을 골라 아래 과제를 해 주세요. ' +
                     '정답을 맞히는 시험이 아니라, 서비스가 쓰기 쉬운지 보려는 과제입니다.');
    },
  },
  {
    title: '과제 1. 고른 기업과, 그 기업에서 "근거 확인" 판정을 받은 약속 1개를 짧게 적어 주세요.',
    add: function (form, title) {
      return form.addTextItem()
        .setTitle(title)
        .setHelpText('예: 기업 이름 / 약속 한 줄. 못 찾으셨으면 "못 찾음"이라고 적어 주세요.')
        .setRequired(true);
    },
  },
  {
    title: '과제 2. 그 약속의 근거가 나온 보고서는 무엇이었나요?',
    add: function (form, title) {
      return form.addMultipleChoiceItem()
        .setTitle(title)
        .setChoiceValues(['2025 사업보고서', '2026 반기보고서', '둘 다', '못 찾음'])
        .setRequired(true);
    },
  },
  {
    title: '과제 3. 서비스에서 찾는 데 걸린 시간은 대략 얼마였나요?',
    add: function (form, title) {
      return form.addMultipleChoiceItem()
        .setTitle(title)
        .setChoiceValues(['1분 이내', '1~2분', '2~4분', '4분 넘게', '못 찾음'])
        .setRequired(true);
    },
  },
  {
    title: '과제 4. 같은 내용을 공시(DART)에서 직접 찾는다면 얼마나 걸릴 것 같나요?',
    add: function (form, title) {
      return form.addMultipleChoiceItem()
        .setTitle(title)
        .setChoiceValues(['5분 이내', '5~15분', '15~30분', '30분 넘게', '잘 모르겠다'])
        .setRequired(false);
    },
  },
];

/**
 * 10/19 추가: 이미 만든 설문을 비대면 참여용으로 고칩니다. 링크는 그대로입니다.
 *   - 안내문에 서비스 주소와 참여 순서를 넣습니다.
 *   - 참가자 번호는 선택으로 바꿉니다. (진행자에게 번호를 받은 사람만 적음)
 *   - '지금 상황' 1문항과 '작은 과제' 머리글·4문항을 사용 소감 앞에 넣습니다.
 * 쓰는 방법: 이 파일 전체를 createSurvey를 실행했던 Apps Script 프로젝트에 붙여 넣고 저장 > 함수 목록에서 updateSurvey 선택 > 실행
 * 응답이 1개라도 있으면 바꾸지 않고 멈춥니다. 이미 있는 문항은 다시 만들지 않으므로,
 * 두 번 실행하거나 중간에 끊긴 뒤 다시 실행해도 문항이 두 번 들어가지 않습니다.
 */
function updateSurvey() {
  const folder = DriveApp.getFolderById(FOLDER_ID);
  const files = folder.getFilesByName(FORM_FILE_NAME);
  if (!files.hasNext()) {
    Logger.log('공통 폴더에서 설문을 찾지 못했습니다. createSurvey를 먼저 실행하세요.');
    return;
  }
  const form = FormApp.openById(files.next().getId());
  const n = form.getResponses().length;
  if (n > 0) {
    Logger.log('이미 응답이 ' + n + '개 있어서 바꾸지 않습니다. (응답이 섞이지 않게 하려는 것입니다)');
    return;
  }

  const items = form.getItems();
  const existing = {};
  for (let i = 0; i < items.length; i++) {
    if (!(items[i].getTitle() in existing)) existing[items[i].getTitle()] = items[i];
  }
  const missing = SELF_TEST_ITEMS.filter(function (spec) { return !(spec.title in existing); });
  if (missing.length === 0) {
    Logger.log('이미 고친 설문입니다. 참가자용 링크: ' + form.getPublishedUrl());
    return;
  }

  form.setDescription(
    '안녕하세요. 수업 Final Project로 만든 기업 조사 AI 서비스 ‘AI Promise’의 사용성 설문입니다 (약 5분).\n' +
    '1) 서비스 주소를 새 창으로 엽니다: ' + SERVICE_URL + '\n' +
    '2) 기업 1곳을 골라 약 3분 동안 써 봅니다.\n' +
    '3) 아래 질문에 답합니다.\n' +
    '이름·연락처·이메일은 수집하지 않습니다. 응답은 서비스 개선과 프로젝트 결과보고서·발표에 집계 형태로 사용되며, ' +
    '자유응답은 익명으로 인용될 수 있습니다. 참여를 원하지 않으면 언제든 중단할 수 있습니다.'
  );

  for (let i = 0; i < items.length; i++) {
    if (items[i].getTitle() === '참가자 번호' && items[i].getType() === FormApp.ItemType.TEXT) {
      const t = items[i].asTextItem();
      t.clearValidation();
      t.setRequired(false);
      t.setHelpText('진행자에게 번호를 받은 경우에만 적어 주세요 (예: P01). 혼자 써 보신 분은 비워 두세요.');
    }
  }

  // 없는 문항만 새로 만들고, 6개 모두를 '참가자 번호' 바로 뒤(동의, 번호 다음인 3번째 자리)부터 순서대로 놓습니다.
  const ordered = SELF_TEST_ITEMS.map(function (spec) {
    return existing[spec.title] || spec.add(form, spec.title);
  });
  let pos = 2;
  ordered.forEach(function (it) {
    form.moveItem(it.getIndex(), pos);
    pos++;
  });

  Logger.log('설문을 비대면 참여용으로 고쳤습니다. 링크는 그대로입니다: ' + form.getPublishedUrl());
  Logger.log('문항 수: ' + form.getItems().length + ' (15면 정상)');
  Logger.log('응답 시트에 새 질문 열이 생깁니다. 응답 시트의 \'요약\' 탭 숫자가 그대로 나오는지 한 번 확인하세요.');
}

// 계정 종류에 따라 지원하지 않는 설정이 있어도 나머지는 계속 만들도록 감쌉니다.
function safe_(label, fn) {
  try {
    fn();
  } catch (e) {
    Logger.log('건너뜀 (' + label + '): ' + e.message);
  }
}
