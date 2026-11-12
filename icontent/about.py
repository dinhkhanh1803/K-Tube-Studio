"""Thông tin tác giả + mời cà phê. K-Tube Studio miễn phí; ủng hộ là hoàn toàn tự nguyện.

Tài khoản và mã VietQR (web/static/donate-qr.png) lấy nguyên từ iNew của cùng tác giả.
"""
from __future__ import annotations

DONATE = {
    "bank": "",
    "account": "",
    "holder": "K-Tube Studio Pro",
    "qr": "",
    "note": "K-Tube Studio - Nền tảng sản xuất video AI",
}

MESSAGE = [
    "K-Tube Studio được làm ra với tinh thần chia sẻ, mong góp một phần nhỏ giúp những người làm nội dung "
    "bớt vất vả hơn mỗi ngày.",
    "Nếu K-Tube Studio đã giúp ích cho công việc của bạn, bạn có thể mời tác giả một ly cà phê. Sự ủng hộ của bạn, "
    "dù nhiều hay ít, là nguồn động viên quý giá để K-Tube Studio tiếp tục được duy trì và hoàn thiện hơn.",
    "Xin chân thành cảm ơn bạn đã đồng hành cùng K-Tube Studio!",
]

VOLUNTARY = "Việc ủng hộ hoàn toàn tự nguyện, không ảnh hưởng đến quyền sử dụng phần mềm."

# hiện một lần sau khi cập nhật (Trang chủ, js/onboard.js): mới nhất trước, viết cho người dùng, không phải cho lập trình viên
CHANGES = [
    {"version": "0.6.1", "date": "11/2026", "items": [
        "Cài xong mà K-Tube Studio không mở được: biểu tượng K-Tube Studio Studio tự mở cửa sổ Sửa lỗi, nói rõ vì sao (thư viện cài chưa xong, thiếu ffmpeg, thiếu bộ chạy Microsoft, cổng bị chiếm, phần mềm diệt virus chặn, mạng bị chặn...) và có nút sửa ngay.",
        "Có biểu tượng Sửa lỗi K-Tube Studio trong menu Start: mở được cả khi K-Tube Studio hỏng hẳn. Kiểm tra máy, cài lại thư viện (chỉ tải phần thiếu), tắt K-Tube Studio bị treo, làm mới cửa sổ K-Tube Studio.",
        "Tạo gói báo lỗi: một nút là có file zip trên màn hình nền gồm nhật ký và kết quả kiểm tra máy để gửi người hỗ trợ. Đã tự bỏ key, cookie, email, tên người dùng và tên máy.",
        "Cài đặt có thêm Kiểm tra máy và Tạo gói báo lỗi; thẻ lỗi chưa có cách sửa sẵn cũng có nút Tạo gói báo lỗi.",
        "Cookie Douyin dễ hơn: bấm Export trong tiện ích là K-Tube Studio tự nhận file trong thư mục Tải về rồi tự thử lại video, không phải kéo thả. Xuất nhầm trang khác (đang đứng ở tab khác) thì báo rõ.",
        "Cookie Douyin đã nạp mà vẫn lỗi: hướng dẫn xử lý ô kéo xác minh, hộp đăng nhập, và có nút Cập nhật bộ tải video ngay trên thẻ lỗi.",
    ]},
    {"version": "0.6.0", "date": "11/2026", "items": [
        "Ưu tiên miễn phí: mục Chi phí mới trong Cài đặt. Đang tắt (mặc định) thì K-Tube Studio chỉ dùng cách miễn phí, nút tính tiền bị khóa, không lo bấm nhầm mất tiền. Muốn dùng bản trả phí thì bật, mỗi lần tốn tiền vẫn báo giá và hỏi trước.",
        "AI viết kịch bản ngay trên máy, không cần key: có Mô-đun AI miễn phí (Dịch offline và Vẽ ảnh offline) là bấm AI viết từ ý tưởng được. Gemini quá tải giữa chừng thì tự viết tiếp bằng AI trên máy.",
        "Nguồn ảnh Tự chọn dùng Vẽ trên máy và Cloudflare miễn phí trước, nguồn trả phí sau.",
        "Kể chuyện có video nền quay thật, miễn phí: bấm Tìm video nền cho mọi cảnh, K-Tube Studio tự nghĩ từ khóa, tìm trong kho Pexels, Pixabay, Wikimedia Commons, chọn clip đúng chủ đề, đúng khung, đủ dài, không trùng nhau rồi tải về. Cảnh có nhân vật của bạn được giữ để vẽ (không chèn người lạ). Muốn tự chọn thì bấm Video nền ở từng cảnh.",
        "Chỉ lấy video có giấy phép dùng thương mại. Nguồn từng clip được ghi vào file .nguon.txt cạnh video và vào mô tả của bộ đăng bài (tác giả, giấy phép), làm bằng chứng khi bị khiếu nại.",
        "AI làm clip: biến ảnh từng cảnh thành clip chuyển động 3 đến 15 giây bằng Google Gemini Omni, giữ đúng nhân vật đã vẽ. Cần key Gemini đã bật thanh toán, khoảng 0,07 USD mỗi giây ở 720p; K-Tube Studio báo giá và hỏi trước khi làm.",
        "Quy trình có 2 mẫu mới: Tổng đạo diễn AI (miễn phí: ý tưởng → kịch bản → video quay thật cho cảnh không người → vẽ cảnh có nhân vật → giọng → nhạc → dựng → đăng) và Truyện có chuyển động bằng clip AI (trả phí, tùy chọn).",
        "Wikimedia Commons dùng được ngay không cần key. Key Pexels, Pixabay miễn phí (đăng ký một phút) cho nhiều video dọc đẹp hơn: dán ở Cài đặt, mục Video nền miễn phí và clip AI.",
    ]},
    {"version": "0.5.0", "date": "11/2026", "items": [
        "Làm video cho thị trường nước ngoài: chọn Lồng tiếng sang ngay ở ô dán link. 22 thứ tiếng: Anh, Indonesia, Thái, Philippines, Malaysia, Tây Ban Nha, Bồ Đào Nha, Nhật, Hàn, Hindi, Ả Rập, Pháp, Đức, Nga, Ý, Thổ Nhĩ Kỳ...",
        "Giọng đọc nhiều thứ tiếng chạy trên máy (Mô-đun AI miễn phí, 2,9 GB): mỗi thứ tiếng 4 giọng nam, nữ, giọng giữ nguyên suốt video, không cần mạng, không bị chặn. Chưa tải thì dùng giọng Microsoft qua mạng.",
        "Dịch theo thị trường: độ dài câu tính theo tốc độ nói của từng thứ tiếng, tên riêng và con số viết theo cách người nước đó đọc; tiêu đề, hashtag cũng theo ngôn ngữ đó. Dịch offline hỗ trợ đủ các thứ tiếng này.",
        "Phụ đề và ảnh bìa hiện đúng chữ Thái, Ả Rập, Hindi, Nhật, Hàn, Khmer, Myanmar (chữ Ả Rập đúng chiều phải sang trái).",
        "Kể chuyện, Đọc văn bản: chọn ngôn ngữ lời dẫn; AI viết kịch bản thẳng bằng ngôn ngữ đó. Giọng của tôi cũng đọc được thứ tiếng khác.",
    ]},
    {"version": "0.4.0", "date": "11/2026", "items": [
        "Mô-đun AI miễn phí (Cài đặt): bấm Tải là có Dịch offline và Vẽ ảnh offline chạy ngay trên máy, không cần key, không cần mạng, không tốn tiền, không phải cài Ollama.",
        "Gemini quá tải, hết lượt trong ngày hay sai key giữa chừng: K-Tube Studio tự dịch tiếp các câu còn lại bằng Dịch offline (rồi Google), video không còn dừng ở bước dịch.",
        "Kể chuyện, Quy trình: thêm nguồn ảnh Vẽ trên máy (miễn phí, không giới hạn số ảnh), giữ nhân vật giống nhau bằng 2 ảnh mẫu.",
        "Tải mô-đun có thanh tiến độ, tốc độ, thời gian còn lại; rớt mạng thì bấm Tải tiếp, không tải lại từ đầu. Tải xong tự chạy thử ngay trên máy.",
        "Đã dùng dịch offline qua Ollama ở bản cũ: K-Tube Studio dùng lại mô hình đó, không phải tải lại 1,1 GB.",
    ]},
    {"version": "0.3.2", "date": "11/2026", "items": [
        "Hết lỗi \"Không kết nối được K-Tube Studio\" khi để cửa sổ lâu, thu nhỏ, hoặc lúc đang ở màn Kích hoạt chờ key: K-Tube Studio không còn tự tắt nhầm khi cửa sổ vẫn mở.",
        "K-Tube Studio bị dừng bất thường (thiếu RAM, phần mềm khác tắt ngang) thì tự chạy lại, cửa sổ tự kết nối lại và tải lại trang.",
        "Gemini quá tải không còn làm video đứng 5-6 phút ở bước Phân tích: quá hơn một phút thì bỏ qua bước phụ này và dịch luôn.",
        "Gặp lỗi là có khung Cách khắc phục: nói rõ vì sao, làm gì, kèm nút sửa ngay (thêm cookie, tải lại mô hình, cập nhật bộ tải video, thử lại).",
        "Douyin: nạp cookie bằng cách kéo thả file theo 4 bước có hướng dẫn, không phải sửa file cấu hình. Nạp xong tự thử lại video.",
        "Link Bilibili có /vi/, /en/ hoặc mã theo dõi (?trackid=) giờ tải được bình thường.",
        "Sửa lỗi giọng đọc VieNeu không chạy trên máy bật Developer Mode (báo ONNXRuntimeError, External data path).",
        "Bilibili báo bận (lỗi 503) thì tự chờ rồi lấy link tải mới, thử lại vài lần trước khi báo lỗi.",
        "Video lỗi ngay bước tải giờ cũng có nút Thử lại; nút Chép thông tin lỗi để gửi tác giả (đã bỏ tên máy).",
    ]},
    {"version": "0.3.1", "date": "11/2026", "items": [
        "Có file cài đặt .exe: bấm đúp, bấm Tiếp là xong; không phải giải nén, không phải cài Python.",
        "Cập nhật bản mới bằng file cài: tự tắt K-Tube Studio đang mở, cài đè đúng thư mục cũ, giữ nguyên video và cấu hình.",
        "Gỡ cài đặt trong Cài đặt Windows > Ứng dụng, có hỏi giữ lại video và cấu hình hay không.",
        "Máy không có winget vẫn tự tải được ffmpeg.",
    ]},
    {"version": "0.3.0", "date": "11/2026", "items": [
        "Kích hoạt miễn phí qua bot Telegram @Kichhoatkey_bot: bấm Nhận key qua Telegram, dán key là xong. Cập nhật bản mới không phải xin lại key.",
        "Không còn lỗi dừng ở bước nhận giọng với một số video (thư viện nhận giọng không gióng được giờ từng từ ở cuối video).",
        "Bỏ câu \"cảm ơn đã xem\" mà máy tự nghe nhầm sau khi video đã hết tiếng.",
        "Dán nhầm key AI thì báo rõ key không đúng và cách chép lại, thay vì mã lỗi khó hiểu.",
    ]},
    {"version": "0.2.0", "date": "11/2026", "items": [
        "Trang chủ mới: chọn việc cần làm, xem việc đang chạy, mọi thứ vừa làm và máy đã sẵn sàng chưa.",
        "Quy trình kéo thả: nối các khối ý tưởng, viết, vẽ, đọc, dựng, thumbnail thành video chỉ với một nút Chạy.",
        "Thumbnail: trình thiết kế ảnh bìa có mẫu sẵn, chữ viền, mũi tên, AI gợi ý chữ, xem thử cỡ điện thoại.",
        "Giọng của tôi: thu 10 giây giọng của bạn để đọc văn bản, kể chuyện bằng chính giọng đó.",
        "Kể chuyện: chỉnh thời lượng từng cảnh, chuyển cảnh, mở đầu và kết thúc; mở câu chuyện trong Trình dựng.",
        "Thư viện gộp: mọi sản phẩm một chỗ, biết món nào nặng, xóa nhiều món một lần, dọn file tạm an toàn.",
        "Có key Gemini là tự dịch bằng Gemini; tự đổi sang model mới khi Google ngừng model cũ.",
        "Báo ở góc màn hình khi video xong hoặc lỗi.",
    ]},
]


def about() -> dict:
    return {"donate": DONATE, "message": MESSAGE, "voluntary": VOLUNTARY, "changes": CHANGES}


def cli_line() -> str:
    return "K-Tube Studio Pro - Nền tảng sản xuất video AI đa ngôn ngữ"
