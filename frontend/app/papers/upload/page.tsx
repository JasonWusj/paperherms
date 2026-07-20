"use client";

import { useState } from "react";
import { CheckCircle2, FileUp, Loader2, UploadCloud } from "lucide-react";
import { PageHeader, StatCard, StatusPill } from "@/components/PageChrome";
import { Panel } from "@/components/Panel";
import { resolveApiBase } from "@/lib/api";

type UploadState = "idle" | "uploading" | "success" | "error";

export default function UploadPage() {
  const [status, setStatus] = useState<UploadState>("idle");
  const [message, setMessage] = useState("等待选择 PDF 文件");
  const [fileName, setFileName] = useState("");

  async function onUpload(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const input = form.elements.namedItem("file") as HTMLInputElement;
    const file = input.files?.[0];
    if (!file) {
      setStatus("error");
      setMessage("请先选择一份 PDF 文件。");
      return;
    }

    setStatus("uploading");
    setMessage("正在上传、解析正文并写入索引...");
    const data = new FormData();
    data.append("file", file);
    const response = await fetch(`${resolveApiBase()}/papers`, { method: "POST", body: data });

    if (response.ok) {
      setStatus("success");
      setMessage("论文已解析并完成索引，可以前往论文库或论文问答继续测试。");
      setFileName("");
      form.reset();
      return;
    }

    setStatus("error");
    setMessage(await response.text());
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="上传论文"
        description="上传 PDF 后，后端会完成文本抽取、章节识别、分块存储和向量索引。完成后即可在论文问答和分析链路中使用。"
        icon={<UploadCloud />}
      />

      <div className="grid gap-4 md:grid-cols-3">
        <StatCard label="第一步" value="选择 PDF" icon={<FileUp />} tone="moss" />
        <StatCard label="第二步" value="解析正文" icon={<Loader2 />} tone="blue" />
        <StatCard label="第三步" value="建立索引" icon={<CheckCircle2 />} tone="rust" />
      </div>

      <Panel title="PDF 上传区">
        <form onSubmit={onUpload} className="space-y-5">
          <label className="flex min-h-72 cursor-pointer flex-col items-center justify-center rounded-lg border border-dashed border-slate-300 bg-slate-50 p-6 text-center transition hover:border-moss hover:bg-white">
            <UploadCloud className="mb-4 h-12 w-12 text-moss" />
            <span className="text-lg font-semibold text-ink">选择 PDF 文件</span>
            <span className="mt-2 max-w-lg text-sm leading-6 text-slate-600">
              建议上传论文原文 PDF。系统会基于解析后的上下文回答问题，上传完成前请保持后端服务运行。
            </span>
            <input
              name="file"
              type="file"
              accept="application/pdf"
              className="mt-6 block max-w-full text-sm text-slate-600"
              onChange={(event) => setFileName(event.target.files?.[0]?.name || "")}
            />
            {fileName ? <span className="mt-3 rounded-md bg-white px-3 py-1 text-xs font-medium text-slate-600">已选择：{fileName}</span> : null}
          </label>

          <div className="flex flex-col gap-3 rounded-lg border border-slate-200 bg-white p-4 md:flex-row md:items-center md:justify-between">
            <div className="flex items-center gap-3">
              <StatusPill
                label={status === "uploading" ? "处理中" : status === "success" ? "已完成" : status === "error" ? "失败" : "待上传"}
                tone={status === "success" ? "green" : status === "error" ? "red" : status === "uploading" ? "amber" : "slate"}
              />
              <span className="text-sm text-slate-600">{message}</span>
            </div>
            <button
              className="inline-flex items-center justify-center gap-2 rounded-md bg-moss px-4 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:bg-slate-400"
              type="submit"
              disabled={status === "uploading"}
            >
              {status === "uploading" ? <Loader2 className="h-4 w-4 animate-spin" /> : <UploadCloud className="h-4 w-4" />}
              上传并解析
            </button>
          </div>
        </form>
      </Panel>
    </div>
  );
}
