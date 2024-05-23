
let page = 1;

const writeButton = document.getElementById("reply-write");
const moreButton = document.getElementById("more-replies");
const ul = document.querySelector("#replies-wrap ul");
const modalContainer = document.getElementById("confirm-modal-container");

// 댓글 목록을 가져와서 화면에 표시하는 함수
const showList = (replies) => {
    let text = ``;
    replies.forEach((reply) => {
        text += `
            <li>
                <div>
                    <div class="comment-user-wrapper-container">
                        <div class="comment-user-wrapper-avatar">
                            <!-- a태그 클릭시 해당 댓글 작성 회원의 마이페이지 이동 -->
<!--                            <a href="">-->
<!--                                <div class="avatar" style="width: 36px; height: 36px;">-->
<!--                                    <span class="avatar-has-image">-->
<!--                                        <img src="/upload/${reply.member_path}" width="15px">-->
<!--                                    </span>-->
<!--                                </div>-->
<!--                            </a>-->
                        </div>
                        <div class="comment-user-wrapper-main">
                            <div class="comment-user-info-container">
                                <span class="comment-user-info-name">
                                    <a href="">
                                        <strong>${reply.member_name}</strong>
                                    </a>
                                </span>
                                <span class="comment-user-info-date">${timeForToday(reply.created_date)}</span>
                                <button class="siren-btn" id="sign" data-reply-id="${reply.id}" type="button" >신고</button>
                            </div>
                            <div>
                                <div class="comment-text-content-container">
                                    <div class="comment-text-content-box"> 
                                        <span class="title">${reply.reply_content}</span>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </li>
        `;
    });
    return text;
}


// 댓글 목록을 가져와서 화면에 표시하는 함수
const displayReplies = (replies) => {
    const html = showList(replies);
    ul.innerHTML = html;

}

function getCSRFToken() {
    const cookies = document.cookie.split(';');
    for (let i = 0; i < cookies.length; i++) {
        const cookie = cookies[i].trim();
        if (cookie.startsWith('csrftoken=')) {
            return cookie.split('=')[1];
        }
    }
    return '';
}

const csrfToken = getCSRFToken();

const addClickEventToButtons = (btn) => {
    btn.addEventListener('click', async (e) => {

        console.log(e.target);
        const replyId = e.target.getAttribute('data-reply-id');
        console.log(replyId)
        const response = await fetch("/ai/review/", {
            method: 'POST',
            headers: {
                "Content-Type": "application/json;charset=utf-8",
                "X-CSRFToken": csrf_token,
            },
            body: JSON.stringify({
                reply_id: replyId
            })
        });
        const results = await response.json();
        console.log(results);
        alert("신고됨");
    })
}
// 예시로 replyService.getList를 호출하여 댓글 목록을 가져오고 화면에 표시

replyService.getList(community_id, page).then((replies) => {
    displayReplies(replies);

    const signBtns = document.querySelectorAll(".siren-btn");
    console.log(signBtns);
    signBtns.forEach((btn)=>{
        console.log(btn);
        addClickEventToButtons(btn);

    })
});

// 모든 신고 버튼을 선택합니다.
// const signBtns = document.querySelectorAll(".siren-btn");
// signBtns.forEach((btn) => {
//     // 각 신고 버튼에 클릭 이벤트 리스너를 추가합니다.
//     btn.addEventListener("click", () => {
//         // 이벤트가 발생했을 때 콘솔에 메시지를 출력합니다.
//         console.log("나옴");
//     });
// });

// function showModal(replyId) {
//     const modalHtml = `
//         <div id="myModal" class="modal">
//           <div class="modal-content">
//             <span class="close">&times;</span>
//             <p>신고 내용을 입력하세요 (댓글 ID: ${replyId}):</p>
//             <textarea id="reportContent"></textarea>
//             <button id="submitReport">신고</button>
//           </div>
//         </div>
//   `;
// }

moreButton.addEventListener("click", (e) => {
    replyService.getList(community_id, ++page, showList).then((text) => {
        ul.innerHTML += text;
    });

    replyService.getList(community_id, page + 1).then((replies) => {
    if (replies.length === 0){
        moreButton.style.display = "none";
    }
});

});

writeButton.addEventListener("click", async (e) => {
    const replyContent = document.getElementById("reply-content");
    await replyService.write({
        reply_content: replyContent.value,
        community_id: community_id
    });
    replyContent.value = "";

    page = 1
    const text = await replyService.getList(community_id, page, showList);
    ul.innerHTML = text;

    const replies = await replyService.getList(community_id, page + 1);
    if (replies.length !== 0){
        moreButton.style.display = "";
    }
    const replyContents = document.getElementById("reply-content").value;
    // const replyElementValue = replyContents.value;

    const response = await fetch("/ai/reviewpredict/", {
        method: 'POST',
        headers: {
            "Content-Type": "application/json;charset=utf-8",
            "X-CSRFToken": csrf_token,
        },
        body: JSON.stringify({
            reply_content: replyContents

        })
    });
    const results = await response.json();
    console.log(results);

    // 서버로부터 'comment' 응답을 받으면 댓글을 삭제합니다.
    if (results === 'comment') {

        // 필요에 따라 추가적인 작업 수행
        alert('댓글이 삭제되었습니다.');
    }

    replyContents.value = "";
});

replyService.getList(community_id, page, showList).then((text) => {
    ul.innerHTML = text;
});

// ul 태그의 자식 태그까지 이벤트가 위임된다.
ul.addEventListener("click", async (e) => {
    if(e.target.classList[0] === 'update'){
        const replyId = e.target.classList[1]
        const updateForm = document.getElementById(`update-form${replyId}`)

        updateForm.style.display = "block";
        updateForm.previousElementSibling.style.display = "none";

    }else if(e.target.classList[0] === 'calcel'){
        const replyId = e.target.classList[1]
        const updateForm = document.getElementById(`update-form${replyId}`)
        updateForm.style.display = "none";
        updateForm.previousElementSibling.style.display = "block";

    }else if(e.target.classList[0] === 'update-done'){
        const replyId = e.target.classList[1]
        const replyContent = document.querySelector(`#update-form${replyId} textarea`);
        await replyService.update({replyId: replyId, replyContent: replyContent.value})
        page = 1
        const text = await replyService.getList(community_id, page, showList);
        ul.innerHTML = text;
        const replies = await replyService.getList(community_id, page + 1);
        if (replies.length !== 0){
            moreButton.style.display = "";
        }

    }else if(e.target.classList[0] === 'delete'){
        const replyId = e.target.classList[1];
        await replyService.remove(replyId);
        page = 1
        const text = await replyService.getList(community_id, page, showList);
        ul.innerHTML = text;

        const replies = await replyService.getList(community_id, page + 1);
        if (replies.length !== 0){
            moreButton.style.display = "";
        }
    }
});

function timeForToday(datetime) {
    const today = new Date();
    const date = new Date(datetime);

    let gap = Math.floor((today.getTime() - date.getTime()) / 1000 / 60);

    if (gap < 1) {
        return "방금 전";
    }

    if (gap < 60) {
        return `${gap}분 전`;
    }

    gap = Math.floor(gap / 60);

    if (gap < 24) {
        return `${gap}시간 전`;
    }

    gap = Math.floor(gap / 24);

    if (gap < 31) {
        return `${gap}일 전`;
    }

    gap = Math.floor(gap / 31);

    if (gap < 12) {
        return `${gap}개월 전`;
    }

    gap = Math.floor(gap / 12);

    return `${gap}년 전`;
}


