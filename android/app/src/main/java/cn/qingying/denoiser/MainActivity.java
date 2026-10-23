package cn.qingying.denoiser;

import android.app.*;
import android.content.*;
import android.graphics.*;
import android.net.Uri;
import android.os.*;
import android.view.*;
import android.widget.*;
import com.chaquo.python.*;
import com.chaquo.python.android.AndroidPlatform;
import java.io.*;
import java.util.concurrent.*;

public class MainActivity extends Activity {
  static {
    System.loadLibrary("qingying");
  }

  public interface NativeProgress {
    void onProgress(int done, int total, String device);
  }

  native String nativeGpuName();
  native String nativeProcess(Bitmap source, Bitmap dest, String root, int engine,
      int strength, int scale, int backend, NativeProgress listener);

  final ExecutorService worker = Executors.newSingleThreadExecutor();
  final String[] modes = {
    "Waifu2x CUNet · 插画降噪",
    "Real-CUGAN · 线条重建",
    "AI Image Rehab · 杂纹清理",
    "非局部均值 · 照片降噪",
    "双边滤波 · 快速保边",
    "中值滤波 · 去除颗粒"
  };
  Spinner algorithm, scale, format, backend;
  SeekBar strength;
  TextView status, strengthText, deviceText;
  Button open, run, save;
  ProgressBar progress;
  Preview preview;
  Bitmap original, result;
  boolean busy = false, dead = false;
  final Handler progressHandler = new Handler(Looper.getMainLooper());
  volatile ProcessingProgress processingProgress;
  final Runnable progressTicker = new Runnable() {
    public void run() {
      if (dead || !busy || processingProgress == null) return;
      renderProgress();
      progressHandler.postDelayed(this, 250);
    }
  };
  File sourceFile, resultFile;
  String exportFormat = "PNG";
  PyObject processor;
  int accent = Color.rgb(32, 100, 91), ink = Color.rgb(26, 45, 43);

  int dp(float x) {
    return (int) (getResources().getDisplayMetrics().density * x + .5f);
  }

  TextView label(String s, int size) {
    TextView t = new TextView(this);
    t.setText(s);
    t.setTextSize(size);
    t.setTextColor(ink);
    return t;
  }

  LinearLayout row() {
    LinearLayout l = new LinearLayout(this);
    l.setOrientation(LinearLayout.HORIZONTAL);
    l.setGravity(Gravity.CENTER_VERTICAL);
    return l;
  }

  Spinner spinner(String[] values) {
    Spinner s = new Spinner(this);
    s.setAdapter(new ArrayAdapter<>(this, android.R.layout.simple_spinner_dropdown_item, values));
    return s;
  }

  Button button(String text) {
    Button b = new Button(this);
    b.setText(text);
    b.setTextColor(accent);
    b.setAllCaps(false);
    return b;
  }

  @Override
  public void onCreate(Bundle state) {
    super.onCreate(state);
    getWindow().setStatusBarColor(Color.rgb(242, 247, 244));
    getWindow().setNavigationBarColor(Color.rgb(242, 247, 244));
    getWindow().getDecorView().setSystemUiVisibility(View.SYSTEM_UI_FLAG_LIGHT_STATUS_BAR);
    sourceFile = new File(getFilesDir(), "source.png");
    resultFile = new File(getFilesDir(), "result.png");
    LinearLayout root = new LinearLayout(this);
    root.setOrientation(LinearLayout.VERTICAL);
    root.setPadding(dp(18), 0, dp(18), 0);
    root.setBackgroundColor(Color.rgb(242, 247, 244));
    root.setOnApplyWindowInsetsListener(
        (v, insets) -> {
          v.setPadding(
              dp(18),
              insets.getSystemWindowInsetTop(),
              dp(18),
              insets.getSystemWindowInsetBottom());
          return insets;
        });
    setContentView(root);
    TextView title = label("清影  ⓘ", 30);
    title.setOnClickListener(v -> showAbout());
    root.addView(title);
    root.addView(label("图片降噪  /  ANDROID", 12));
    preview = new Preview();
    LinearLayout.LayoutParams pv = new LinearLayout.LayoutParams(-1, 0, 1);
    pv.topMargin = dp(14);
    pv.bottomMargin = dp(10);
    root.addView(preview, pv);
    LinearLayout tabs = row();
    for (int i = 0; i < 3; i++) {
      final int v = i;
      Button b = button(new String[] {"原图", "结果", "分割对比"}[i]);
      b.setOnClickListener(
          w -> {
            preview.mode = v;
            preview.invalidate();
          });
      tabs.addView(b, new LinearLayout.LayoutParams(0, dp(44), 1));
    }
    root.addView(tabs);
    ScrollView controls = new ScrollView(this);
    LinearLayout panel = new LinearLayout(this);
    panel.setOrientation(LinearLayout.VERTICAL);
    controls.addView(panel);
    root.addView(controls, new LinearLayout.LayoutParams(-1, dp(262)));
    algorithm = spinner(modes);
    panel.addView(algorithm);
    backend = spinner(new String[] {"自动 · 优先 GPU", "CPU · 兼容模式"});
    backend.setSelection(getPreferences(MODE_PRIVATE).getInt("backend", 0) == 1 ? 1 : 0);
    backend.setOnItemSelectedListener(new AdapterView.OnItemSelectedListener() {
      public void onNothingSelected(AdapterView<?> parent) {}
      public void onItemSelected(AdapterView<?> parent, View view, int position, long id) {
        getPreferences(MODE_PRIVATE).edit().putInt("backend", position).apply();
      }
    });
    panel.addView(backend);
    deviceText = label("正在检测 Vulkan GPU…", 12);
    panel.addView(deviceText);
    LinearLayout options = row();
    options.addView(label("输出倍率", 14));
    scale = spinner(new String[] {"1×", "2×", "4×"});
    options.addView(scale, new LinearLayout.LayoutParams(0, dp(46), 1));
    format = spinner(new String[] {"PNG", "JPEG", "WEBP"});
    options.addView(format, new LinearLayout.LayoutParams(0, dp(46), 1));
    panel.addView(options);
    strengthText = label("降噪强度：中", 14);
    panel.addView(strengthText);
    strength = new SeekBar(this);
    strength.setMax(2);
    strength.setProgress(1);
    panel.addView(strength);
    strength.setOnSeekBarChangeListener(
        new SeekBar.OnSeekBarChangeListener() {
          public void onStartTrackingTouch(SeekBar s) {}

          public void onStopTrackingTouch(SeekBar s) {}

          public void onProgressChanged(SeekBar s, int p, boolean u) {
            updateStrength();
          }
        });
    algorithm.setOnItemSelectedListener(
        new android.widget.AdapterView.OnItemSelectedListener() {
          public void onNothingSelected(AdapterView<?> p) {}

          public void onItemSelected(AdapterView<?> p, View v, int n, long id) {
            String[] values =
                n == 0
                    ? new String[] {"1×", "2×", "4×"}
                    : n == 1 ? new String[] {"1×", "2×", "3×", "4×"} : new String[] {"1×"};
            scale.setAdapter(
                new ArrayAdapter<>(
                    MainActivity.this, android.R.layout.simple_spinner_dropdown_item, values));
            strength.setMax(n < 3 ? 2 : 29);
            strength.setProgress(n < 3 ? 1 : 9);
            updateStrength();
          }
        });
    scale.setOnItemSelectedListener(
        new AdapterView.OnItemSelectedListener() {
          public void onNothingSelected(AdapterView<?> p) {}

          public void onItemSelected(AdapterView<?> p, View v, int n, long id) {
            updateStrength();
          }
        });
    progress = new ProgressBar(this, null, android.R.attr.progressBarStyleHorizontal);
    progress.setMax(100);
    progress.setIndeterminate(true);
    progress.setVisibility(View.INVISIBLE);
    root.addView(progress, new LinearLayout.LayoutParams(-1, dp(4)));
    status = label("本地离线处理 · 图片不会上传", 12);
    status.setPadding(0, dp(6), 0, dp(6));
    status.setMinLines(3);
    status.setAccessibilityLiveRegion(View.ACCESSIBILITY_LIVE_REGION_POLITE);
    root.addView(status);
    LinearLayout actions = row();
    open = button("打开图片");
    run = button("开始降噪");
    save = button("保存结果");
    actions.addView(open, new LinearLayout.LayoutParams(0, dp(52), 1));
    actions.addView(run, new LinearLayout.LayoutParams(0, dp(52), 1));
    actions.addView(save, new LinearLayout.LayoutParams(0, dp(52), 1));
    root.addView(actions);
    open.setOnClickListener(
        v ->
            startActivityForResult(
                new Intent(Intent.ACTION_OPEN_DOCUMENT)
                    .setType("image/*")
                    .addCategory(Intent.CATEGORY_OPENABLE),
                1));
    run.setOnClickListener(v -> process());
    save.setOnClickListener(
        v -> {
          exportFormat = format.getSelectedItem().toString();
          String ext =
              exportFormat.equals("JPEG") ? "jpg" : exportFormat.toLowerCase(java.util.Locale.ROOT);
          startActivityForResult(
              new Intent(Intent.ACTION_CREATE_DOCUMENT)
                  .addCategory(Intent.CATEGORY_OPENABLE)
                  .setType(exportFormat.equals("JPEG") ? "image/jpeg" : "image/" + ext)
                  .putExtra(Intent.EXTRA_TITLE, "清影_" + System.currentTimeMillis() + "." + ext),
              2);
        });
    setBusy(true, "正在初始化本地引擎…");
    worker.execute(
        () -> {
          try {
            if (!Python.isStarted()) Python.start(new AndroidPlatform(this));
            processor = Python.getInstance().getModule("processing");
            copyAssets("models-cunet");
            copyAssets("models-se");
            final String gpu = nativeGpuName();
            Bitmap restoredSource = sourceFile.isFile() ? decode(sourceFile) : null;
            Bitmap restoredResult =
                restoredSource != null && resultFile.isFile() ? decode(resultFile) : null;
            ui(
                () -> {
                  deviceText.setText(gpu == null || gpu.isEmpty()
                      ? "当前设备使用 CPU · 未检测到可用 Vulkan GPU"
                      : "可用 GPU：" + gpu + " · 仅加速两种 AI 算法");
                  original = restoredSource;
                  result = restoredResult;
                  preview.reset();
                  setBusy(false, "本地离线处理 · 图片不会上传");
                });
          } catch (Throwable e) {
            fail(e);
          }
        });
  }

  void showAbout() {
    StringBuilder text =
        new StringBuilder(
            "清影 Android · GPU 预览版\n\n"
                + "所有处理均在手机本地完成。两种 AI 算法自动优先使用 Vulkan GPU，可切换 CPU；其余算法使用 CPU。大图可能耗时较长。\n\n"
                + "Waifu2x：1/2/4×；Real-CUGAN：1/2/3/4×，3/4× 固定高强度。其他算法为 1×。\n\n"
                + "AI 进度按实际完成的图块步骤统计，显示耗时、速度和预计剩余时间；其他算法显示处理阶段。\n\n双指缩放，拖动分割线对比。JPEG 将透明区域合成为白色。导出不保留 EXIF/GPS/ICC 信息。\n\n"
                + "手机首版暂不提供批量处理。处理时请保持应用打开。\n\n"
                + "第三方组件与许可：\n");
    try {
      appendLicenses("licenses", text);
    } catch (IOException e) {
      text.append(e.getMessage());
    }
    TextView content = label(text.toString(), 13);
    content.setPadding(dp(18), dp(12), dp(18), dp(12));
    ScrollView scroll = new ScrollView(this);
    scroll.addView(content);
    new AlertDialog.Builder(this)
        .setTitle("关于清影 / 许可")
        .setView(scroll)
        .setPositiveButton("关闭", null)
        .show();
  }

  void appendLicenses(String path, StringBuilder text) throws IOException {
    String[] names = getAssets().list(path);
    if (names.length > 0) {
      for (String name : names) appendLicenses(path + "/" + name, text);
    } else {
      try (InputStream in = getAssets().open(path);
          ByteArrayOutputStream out = new ByteArrayOutputStream()) {
        copy(in, out);
        text.append("\n\n—— ").append(path).append(" ——\n").append(out.toString("UTF-8"));
      }
    }
  }

  void copyAssets(String folder) throws IOException {
    File dir = new File(getFilesDir(), folder);
    dir.mkdirs();
    for (String name : getAssets().list(folder)) {
      File dest = new File(dir, name);
      if (dest.exists() && dest.length() > 0) continue;
      File temp = new File(dir, name + ".tmp");
      try (InputStream in = getAssets().open(folder + "/" + name);
          OutputStream out = new FileOutputStream(temp)) {
        copy(in, out);
      }
      if (!temp.renameTo(dest)) throw new IOException("模型初始化失败");
    }
  }

  static void copy(InputStream in, OutputStream out) throws IOException {
    byte[] buf = new byte[65536];
    int n;
    while ((n = in.read(buf)) != -1) out.write(buf, 0, n);
  }

  void ui(Runnable r) {
    runOnUiThread(
        () -> {
          if (!dead) r.run();
        });
  }

  int factor() {
    return Integer.parseInt(scale.getSelectedItem().toString().replace("×", ""));
  }

  void updateStrength() {
    if (strength == null || scale.getSelectedItem() == null) return;
    boolean fixed = algorithm.getSelectedItemPosition() == 1 && factor() >= 3;
    if (fixed) strength.setProgress(2);
    strength.setEnabled(!busy && !fixed);
    int n = strength.getProgress() + 1;
    strengthText.setText(
        "降噪强度："
            + (algorithm.getSelectedItemPosition() < 3
                ? new String[] {"低", "中", "高"}[Math.min(n - 1, 2)]
                : n)
            + (fixed ? "（此倍率仅支持高强度）" : ""));
  }

  void setBusy(boolean b, String message) {
    busy = b;
    progressHandler.removeCallbacks(progressTicker);
    if (b) {
      progress.setIndeterminate(true);
      progress.setProgress(0);
      processingProgress = new ProcessingProgress(SystemClock.elapsedRealtime());
      processingProgress.stage(message);
      progressHandler.post(progressTicker);
    } else {
      processingProgress = null;
    }
    if (b) getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
    else getWindow().clearFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
    open.setEnabled(!b);
    run.setEnabled(!b && original != null);
    save.setEnabled(!b && result != null);
    algorithm.setEnabled(!b);
    backend.setEnabled(!b);
    scale.setEnabled(!b);
    format.setEnabled(!b);
    progress.setVisibility(b ? View.VISIBLE : View.INVISIBLE);
    status.setText(message);
    updateStrength();
  }

  static String duration(long seconds) {
    return seconds >= 3600
        ? String.format(java.util.Locale.ROOT, "%d:%02d:%02d", seconds / 3600, seconds / 60 % 60, seconds % 60)
        : String.format(java.util.Locale.ROOT, "%02d:%02d", seconds / 60, seconds % 60);
  }

  void renderProgress() {
    ProcessingProgress tracker = processingProgress;
    if (tracker == null) return;
    ProcessingProgress.Snapshot s = tracker.snapshot(SystemClock.elapsedRealtime());
    progress.setIndeterminate(!s.measurable);
    String elapsed = "已用 " + duration(s.elapsed / 1000);
    if (s.measurable) {
      progress.setProgress(s.percent());
      String estimate = s.rate > 0
          ? String.format(java.util.Locale.ROOT, "%.2f 步/秒 · 剩余约 %s", s.rate, duration(s.remaining))
          : "正在估算速度与剩余时间";
      status.setText("AI 推理 " + s.percent() + "%"
          + (s.passes > 1 ? " · 第 " + s.pass + "/" + s.passes + " 轮" : "")
          + " · " + s.completed + "/" + s.total + " 图块步骤\n"
          + s.device + "\n" + elapsed + " · " + estimate);
      progress.setContentDescription("AI 推理已完成百分之" + s.percent());
    } else {
      status.setText(s.stage + (s.device.isEmpty() ? "" : " · " + s.device)
          + "\n" + elapsed + "\n此阶段尚无可计算的剩余时间");
      progress.setContentDescription(s.stage);
    }
  }

  // Called from Python on the worker thread, never directly mutates Android views.
  public void onPythonStage(String stage) {
    ProcessingProgress tracker = processingProgress;
    if (tracker != null) tracker.stage(stage);
  }

  void fail(Throwable e) {
    ui(
        () -> {
          setBusy(false, "处理未完成，可调整参数后重试");
          new AlertDialog.Builder(this)
              .setTitle("清影提示")
              .setMessage(
                  e instanceof OutOfMemoryError
                      ? "内存不足，请使用较小图片或降低输出倍率。"
                      : String.valueOf(e.getMessage()))
              .setPositiveButton("知道了", null)
              .show();
        });
  }

  @Override
  protected void onActivityResult(int request, int code, Intent data) {
    super.onActivityResult(request, code, data);
    if (code != RESULT_OK || data == null || data.getData() == null) return;
    Uri uri = data.getData();
    if (request == 1) {
      setBusy(true, "正在读取图片…");
      worker.execute(
          () -> {
            File incoming = new File(getCacheDir(), "incoming");
            File prepared = new File(getCacheDir(), "prepared.png");
            try {
              try (InputStream in = getContentResolver().openInputStream(uri);
                  OutputStream out = new FileOutputStream(incoming)) {
                copy(in, out);
              }
              processor.callAttr("prepare", incoming.getPath(), prepared.getPath());
              Bitmap bitmap = decode(prepared);
              if (bitmap == null) throw new IOException("无法解码图片");
              if (!prepared.renameTo(sourceFile)) throw new IOException("无法保存导入图片");
              resultFile.delete();
              ui(
                  () -> {
                    original = bitmap;
                    result = null;
                    preview.reset();
                    setBusy(false, bitmap.getWidth() + " × " + bitmap.getHeight() + " · 已载入");
                  });
            } catch (Throwable e) {
              fail(e);
            } finally {
              incoming.delete();
              prepared.delete();
            }
          });
    } else if (request == 2) {
      setBusy(true, "正在导出图片…");
      worker.execute(
          () -> {
            File temp = new File(getCacheDir(), "export");
            try {
              processor.callAttr("export", resultFile.getPath(), temp.getPath(), exportFormat);
              try (InputStream in = new FileInputStream(temp);
                  OutputStream out = getContentResolver().openOutputStream(uri, "wt")) {
                copy(in, out);
              }
              ui(() -> setBusy(false, "已保存到所选位置"));
            } catch (Throwable e) {
              fail(e);
            } finally {
              temp.delete();
            }
          });
    }
  }

  Bitmap decode(File file) {
    BitmapFactory.Options o = new BitmapFactory.Options();
    o.inPreferredConfig = Bitmap.Config.ARGB_8888;
    return BitmapFactory.decodeFile(file.getPath(), o);
  }

  void process() {
    if (busy || original == null) return;
    final int mode = algorithm.getSelectedItemPosition(),
        s = strength.getProgress() + 1,
        f = factor(),
        selectedBackend = backend.getSelectedItemPosition();
    int peakFactor = mode == 1 && f == 1 ? 2 : f;
    long pixels = (long) original.getWidth() * original.getHeight() * peakFactor * peakFactor;
    long limit =
        Math.min(
            16000000, Runtime.getRuntime().maxMemory() / (mode == 2 ? 240 : mode < 2 ? 64 : 48));
    if (pixels > limit) {
      new AlertDialog.Builder(this)
          .setMessage("预计输出超出当前设备的安全内存范围，请缩小图片或降低倍率。")
          .setPositiveButton("知道了", null)
          .show();
      return;
    }
    setBusy(true, "正在准备处理…");
    final ProcessingProgress tracker = processingProgress;
    worker.execute(
        () -> {
          File temp = new File(getCacheDir(), "processed.png");
          try {
            Bitmap output;
            String usedBackend = "CPU";
            String fallbackNote = "";
            if (mode < 2) {
              Bitmap current = original;
              int passes = mode == 0 && f == 4 ? 2 : 1;
              int totalWork = ProcessingProgress.tiles(original.getWidth(), original.getHeight(), mode);
              if (passes == 2) totalWork += ProcessingProgress.tiles(original.getWidth() * 2, original.getHeight() * 2, mode);
              int completedWork = 0;
              int requestedBackend = selectedBackend;
              for (int i = 0; i < passes; i++) {
                int work = ProcessingProgress.tiles(current.getWidth(), current.getHeight(), mode);
                tracker.beginPass(completedWork, work, totalWork, i + 1, passes);
                int sf = mode == 0 ? (f == 1 ? 1 : 2) : (f == 1 ? 2 : f);
                Bitmap next =
                    Bitmap.createBitmap(
                        current.getWidth() * sf, current.getHeight() * sf, Bitmap.Config.ARGB_8888);
                try {
                  usedBackend = nativeProcess(current, next, getFilesDir().getPath(), mode, s, sf,
                      requestedBackend, (done, count, device) ->
                          tracker.update(done, count, device, SystemClock.elapsedRealtime()));
                } catch (Throwable e) {
                  next.recycle();
                  if (current != original) current.recycle();
                  throw e;
                }
                if (usedBackend.startsWith("CPU")) requestedBackend = 1;
                if (usedBackend.contains("已回退")) fallbackNote = "（GPU 执行失败，已回退）";
                completedWork += work;
                if (current != original) current.recycle();
                current = next;
              }
              tracker.stage("AI 推理已完成 · 正在整理与编码结果");
              if (mode == 1 && f == 1) {
                output =
                    Bitmap.createScaledBitmap(
                        current, original.getWidth(), original.getHeight(), true);
                current.recycle();
              } else output = current;
              try (OutputStream out = new FileOutputStream(temp)) {
                if (!output.compress(Bitmap.CompressFormat.PNG, 100, out))
                  throw new IOException("编码失败");
              }
            } else {
              processor.callAttr("process", sourceFile.getPath(), temp.getPath(), mode, s, this);
              output = decode(temp);
            }
            if (output == null) throw new IOException("处理结果为空");
            if (!temp.renameTo(resultFile)) throw new IOException("无法保存处理结果");
            final Bitmap ready = output;
            final String finalBackend = mode < 2
                ? (usedBackend.equals("CPU") ? usedBackend + fallbackNote : usedBackend) : "CPU";
            final long elapsed = tracker.snapshot(SystemClock.elapsedRealtime()).elapsed;
            final double megapixelsPerSecond = (long) original.getWidth() * original.getHeight()
                / 1000000.0 / Math.max(.001, elapsed / 1000.0);
            ui(
                () -> {
                  result = ready;
                  preview.mode = 2;
                  preview.reset();
                  setBusy(
                      false,
                      "处理完成 · " + ready.getWidth() + " × " + ready.getHeight() + " · " + finalBackend
                          + "\n总用时 " + duration(elapsed / 1000)
                          + String.format(java.util.Locale.ROOT, " · %.3f MP/秒（输入像素）", megapixelsPerSecond)
                          + "\n拖动分割线对比，可保存结果");
                });
          } catch (Throwable e) {
            fail(e);
          } finally {
            temp.delete();
          }
        });
  }

  @Override
  protected void onDestroy() {
    dead = true;
    progressHandler.removeCallbacks(progressTicker);
    worker.shutdown();
    super.onDestroy();
  }

  class Preview extends View {
    Paint paint = new Paint(3);
    RectF imageRect = new RectF();
    int mode = 2;
    float split = .5f, zoom = 1, panX = 0, panY = 0, lastX, lastY;
    boolean divider;
    ScaleGestureDetector pinch =
        new ScaleGestureDetector(
            MainActivity.this,
            new ScaleGestureDetector.SimpleOnScaleGestureListener() {
              public boolean onScale(ScaleGestureDetector d) {
                zoom = Math.max(1, Math.min(8, zoom * d.getScaleFactor()));
                invalidate();
                return true;
              }
            });

    Preview() {
      super(MainActivity.this);
      setLayerType(View.LAYER_TYPE_SOFTWARE, null);
    }

    void reset() {
      zoom = 1;
      panX = panY = 0;
      invalidate();
    }

    void image(Canvas c, Bitmap b, RectF rect) {
      if (b != null) c.drawBitmap(b, null, rect, paint);
    }

    protected void onDraw(Canvas c) {
      super.onDraw(c);
      c.drawColor(Color.rgb(224, 234, 229));
      if (original == null) {
        paint.setColor(accent);
        paint.setTextSize(dp(18));
        paint.setTextAlign(Paint.Align.CENTER);
        c.drawText("让细节清晰，让噪点安静", getWidth() / 2f, getHeight() / 2f, paint);
        paint.setTextSize(dp(12));
        c.drawText("打开一张图片，开始本地降噪", getWidth() / 2f, getHeight() / 2f + dp(28), paint);
        return;
      }
      float fit =
          Math.min(
              (float) getWidth() / original.getWidth(), (float) getHeight() / original.getHeight());
      float w = original.getWidth() * fit * zoom, h = original.getHeight() * fit * zoom;
      RectF rect = imageRect;
      rect.set(
          (getWidth() - w) / 2 + panX,
          (getHeight() - h) / 2 + panY,
          (getWidth() + w) / 2 + panX,
          (getHeight() + h) / 2 + panY);
      image(c, mode == 1 && result != null ? result : original, rect);
      if (mode == 2 && result != null) {
        c.save();
        c.clipRect(getWidth() * split, 0, getWidth(), getHeight());
        image(c, result, rect);
        c.restore();
        paint.setColor(Color.WHITE);
        paint.setStrokeWidth(dp(2));
        c.drawLine(getWidth() * split, 0, getWidth() * split, getHeight(), paint);
        c.drawCircle(getWidth() * split, getHeight() / 2f, dp(9), paint);
      }
      paint.setTextSize(dp(12));
      paint.setTextAlign(Paint.Align.LEFT);
      paint.setColor(accent);
      c.drawText("双指缩放 · 拖动画面 · 双击复位", dp(10), getHeight() - dp(12), paint);
    }

    @Override
    public boolean performClick() {
      super.performClick();
      reset();
      return true;
    }

    long lastTap;

    public boolean onTouchEvent(android.view.MotionEvent e) {
      pinch.onTouchEvent(e);
      float x = e.getX(), y = e.getY();
      if (e.getActionMasked() == MotionEvent.ACTION_DOWN) {
        divider = mode == 2 && Math.abs(x - getWidth() * split) < dp(30);
        lastX = x;
        lastY = y;
        if (e.getEventTime() - lastTap < 280) reset();
        lastTap = e.getEventTime();
      } else if (e.getActionMasked() == MotionEvent.ACTION_MOVE) {
        if (!pinch.isInProgress() && e.getPointerCount() == 1) {
          if (divider) split = Math.max(0, Math.min(1, x / getWidth()));
          else {
            panX += x - lastX;
            panY += y - lastY;
          }
        }
        lastX = x;
        lastY = y;
        invalidate();
      }
      if (e.getActionMasked() == MotionEvent.ACTION_UP) super.performClick();
      return true;
    }
  }
}
