# FastAPI 版本的 API 服务器
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
import sys
import os
import time

# 添加核心模块路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'core'))

app = FastAPI(
    title="CRIM Pieces Analysis API",
    description="A modern API for musical piece analysis using FastAPI",
    version="2.0.0",
    docs_url="/docs",  # Swagger UI at http://localhost:9000/docs
    redoc_url="/redoc"  # ReDoc at http://localhost:9000/redoc
)

# CORS 配置 - FastAPI 的 CORS 处理更加完善
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 开发环境允许所有来源
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# 请求日志中间件
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    
    print(f"{request.method} {request.url} - {response.status_code} - {process_time:.2f}s")
    return response

# 健康检查
@app.get("/health")
async def health_check():
    return {
        "status": "healthy", 
        "service": "pieces-api", 
        "version": "2.0.0",
        "timestamp": int(time.time())
    }

# 根路径
@app.get("/")
async def root():
    return {
        "message": "CRIM Pieces Analysis API v2.0 (FastAPI)",
        "documentation": {
            "swagger_ui": "/docs",
            "redoc": "/redoc"
        },
        "endpoints": {
            "pieces": "/pieces",
            "piece_by_id": "/pieces/{id}",
            "note_sets": "/note-sets",
            "health": "/health"
        }
    }

# 导入现有的路由逻辑
try:
    from routes.pieces import pieces_bp
    print("成功导入现有的 pieces 路由")
except ImportError as e:
    print(f"无法导入现有路由: {e}")
    pieces_bp = None

# API路由 - 重新实现现有功能
@app.get("/pieces")
async def get_all_pieces():
    """获取所有音乐作品"""
    try:
        from db_utils import get_all_pieces_from_db
        pieces_data = get_all_pieces_from_db()
        return pieces_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取作品列表失败: {str(e)}")

@app.get("/pieces/{piece_id}")
async def get_piece_by_id(piece_id: int):
    """根据ID获取特定音乐作品"""
    try:
        from db_utils import get_piece_by_id_from_db
        piece_data = get_piece_by_id_from_db(piece_id)
        if not piece_data:
            raise HTTPException(status_code=404, detail="作品未找到")
        return piece_data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取作品失败: {str(e)}")

@app.get("/note-sets")
async def get_all_note_sets():
    """获取所有音符集合"""
    try:
        from db_utils import get_all_note_sets_from_db
        note_sets_data = get_all_note_sets_from_db()
        return note_sets_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取音符集合失败: {str(e)}")

@app.get("/pieces/{piece_id}/notes")
async def get_piece_notes(piece_id: int, note_set_id: int = 1):
    """获取作品的音符数据"""
    try:
        from db_utils import get_notes_for_piece_from_db
        notes_data = get_notes_for_piece_from_db(piece_id, note_set_id)
        return notes_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取音符数据失败: {str(e)}")

@app.get("/pieces/{piece_id}/musicxml")
async def get_piece_musicxml(piece_id: int):
    """获取作品的MusicXML文件"""
    try:
        from db_utils import get_piece_by_id_from_db
        piece_data = get_piece_by_id_from_db(piece_id)
        
        if not piece_data or not piece_data.get('success'):
            raise HTTPException(status_code=404, detail="作品未找到")
        
        piece = piece_data['data']
        
        # 构建MusicXML文件路径
        import os
        project_root = os.path.dirname(os.path.dirname(__file__))
        xml_path = os.path.join(project_root, 'data', piece['path'])
        
        if not os.path.exists(xml_path):
            raise HTTPException(status_code=404, detail="MusicXML文件未找到")
        
        with open(xml_path, 'r', encoding='utf-8') as f:
            xml_content = f.read()
        
        return PlainTextResponse(xml_content, media_type="application/xml")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取MusicXML失败: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    print("🚀 启动 FastAPI 服务器...")
    print("📖 API 文档: http://localhost:9000/docs")
    print("📚 ReDoc 文档: http://localhost:9000/redoc")
    print("🌐 局域网访问: http://10.113.82.229:9000/docs")
    uvicorn.run(
        "fastapi_app:app",  # 作为导入字符串
        host="0.0.0.0", 
        port=9000,
        reload=True,  # 现在可以正常工作
        log_level="info"
    )
