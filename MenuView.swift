//
//  MenuView.swift
//  سبحة — اختيار المجموعات + الإعدادات + رسالة إتمام المجموعة
//

import SwiftUI

// MARK: - قائمة المجموعات والإعدادات

struct MenuView: View {

    @EnvironmentObject private var model: CounterModel
    @EnvironmentObject private var session: SessionManager
    @Binding var nightMode: Bool
    /// لعرض شاشة الترحيب من جديد
    @Binding var showOnboarding: Bool
    @State private var showStats = false

    var body: some View {
        NavigationStack {
            List {

                // ───── المجموعات ─────
                Section("المجموعات") {
                    ForEach(Array(adhkarSets.enumerated()), id: \.element.id) { index, set in
                        Button {
                            model.selectSet(index)
                        } label: {
                            HStack(spacing: 8) {
                                Image(systemName: set.symbol)
                                    .font(.system(size: 12))
                                    .foregroundStyle(index == model.s.setIndex ? .teal : .secondary)

                                VStack(alignment: .leading, spacing: 1) {
                                    Text(set.title)
                                        .font(.system(size: 13, weight: .medium))
                                        .lineLimit(1)
                                    Text("\(set.items.count) أذكار" +
                                         (set.totalCount > 0 ? " · \(set.totalCount) ضغطة" : " · بلا حد"))
                                        .font(.system(size: 9))
                                        .foregroundStyle(.secondary)
                                }

                                Spacer()

                                if index == model.s.setIndex {
                                    Image(systemName: "checkmark")
                                        .font(.system(size: 11, weight: .bold))
                                        .foregroundStyle(.teal)
                                }
                            }
                        }
                        .buttonStyle(.plain)
                    }
                }

                // ───── الجلسة الحالية ─────
                Section("الجلسة") {
                    HStack(spacing: 4) {
                        Image(systemName: session.isActive ? "bolt.fill" : "bolt.slash")
                            .font(.system(size: 10))
                            .foregroundStyle(session.isActive ? .green : .orange)
                        Text(session.statusText)
                            .font(.system(size: 10))
                    }
                    Text("العدّ يستمر بعد انطفاء الشاشة. الإيماءة تحتاج شاشة مضيئة، فاترك واجهة الساعة متجهة نحوك.")
                        .font(.system(size: 10))
                        .foregroundStyle(.secondary)
                }

                // ───── العرض ─────
                Section("طريقة العرض") {
                    Toggle("وضع القراءة (النص كاملًا)", isOn: $model.readingMode)

                    if model.readingMode {
                        Picker("حجم الخط", selection: $model.fontScaleIndex) {
                            Text("صغير").tag(0)
                            Text("متوسط").tag(1)
                            Text("كبير").tag(2)
                        }
                        .pickerStyle(.wheel)

                        Toggle("العدّاد في يمين الشاشة", isOn: $model.badgeOnRight)
                    }

                    Text("في وضع القراءة يملأ نص الذكر الشاشة، والعدّاد حلقة صغيرة في الزاوية — مثالي لآية الكرسي وسيد الاستغفار.")
                        .font(.system(size: 9))
                        .foregroundStyle(.secondary)
                }

                // ───── التلقين (تمرير تلقائي) ─────
                Section("التلقين") {
                    Toggle("تمرير تلقائي للقراءة", isOn: $model.autoScroll)

                    if model.autoScroll {
                        Picker("الوتيرة", selection: $model.scrollSpeedIndex) {
                            Text("هادئ").tag(0)
                            Text("متوسط").tag(1)
                            Text("سريع").tag(2)
                        }
                        .pickerStyle(.wheel)

                        Text("الوتيرة الحالية: \(model.wpmLabel) كلمة/دقيقة — يتحرك النص تلقائيًا حتى نهايته، ثم يتوقف بإشارة اهتزاز.")
                            .font(.system(size: 9))
                            .foregroundStyle(.secondary)
                    }
                }

                // ───── الرؤية من بعيد ─────
                Section("الرؤية من بعيد") {
                    Toggle("نص أكبر وأسمك", isOn: $model.distanceMode)

                    Picker("خط القراءة", selection: $model.fontFamilyIndex) {
                        Text("خط النظام").tag(0)
                        Text("أميري (نسخي)").tag(1)
                        Text("المراعي (عصري)").tag(2)
                    }

                    Text("الخطوط مرفقة داخل التطبيق: «أميري» نسخي قرآنّي لتشكيل واضح، و«المراعي» عصري للواجهة." +
                         " وإن لم تُحمَّل الخطوط لأي سبب، يرجع التطبيق لخط النظام تلقائيًا بلا أي خطأ.")
                        .font(.system(size: 9))
                        .foregroundStyle(.secondary)
                }

                // ───── أدوات ─────
                Section("أدوات") {
                    Button { showStats = true } label: {
                        Label("إحصاءاتك", systemImage: "chart.bar.xaxis")
                    }
                    Button { showOnboarding = true } label: {
                        Label("كيف أستخدم السبحة؟", systemImage: "questionmark.circle")
                    }
                    // 📜 صفحة المصادر — قرار المستخدم: في القائمة فقط، بلا سطر على شاشة العدّاد
                    NavigationLink {
                        SourcesView()
                    } label: {
                        Label("المصادر والمراجع", systemImage: "book.closed")
                    }
                }

                // ───── الصوت والاهتزاز ─────
                Section("الصوت والاهتزاز") {
                    Toggle("صوت نقرة ونغمة", isOn: Binding(
                        get: { model.soundEnabled },
                        set: { on in
                            model.soundEnabled = on
                            model.persistDisplay()
                            if on { Sounds.play(.click) }     // ليسمع النتيجة فورًا
                        }
                    ))

                    Picker("شدة الاهتزاز", selection: Binding(
                        get: { model.hapticLevelIndex },
                        set: { i in
                            model.hapticLevelIndex = i
                            model.persistDisplay()
                            Haptics.tick()                 // ليجرّب الشدّة فورًا
                        }
                    )) {
                        Text("ناعم").tag(0)
                        Text("متوسط").tag(1)
                        Text("قوي").tag(2)
                    }
                }

                // ───── الإعدادات ─────
                Section("الإعدادات") {
                    Toggle("الانتقال التلقائي", isOn: $model.autoAdvance)
                    Toggle("الاهتزاز", isOn: $model.hapticsEnabled)
                    Toggle("الوضع الليلي", isOn: $nightMode)
                }

                // ───── إجراءات ─────
                Section {
                    Button("إعادة المجموعة من الأول") { model.restartSet() }
                    Button("تصفير الذكر الحالي")     { model.resetCurrent() }
                }

                Section {
                    Text("عدّل المجموعات أو أضف غيرها من ملف Shared.swift — التطبيق كله يقرأ منها.")
                        .font(.system(size: 9))
                        .foregroundStyle(.tertiary)
                }
            }
            .navigationTitle("سُبحة")
        }
        .sheet(isPresented: $showStats) {
            NavigationStack { StatsView() }
        }
        .onAppear {
            #if DEBUG
            // 📸 لقطات المتجر: فتح الإحصاءات تلقائيًا عند طلبها (التطوير فقط)
            if SabhaShot.isActive("stats") {
                Task { @MainActor in
                    try? await Task.sleep(nanoseconds: 700_000_000)
                    showStats = true
                }
            }
            #endif
        }
    }
}

// MARK: - صفحة المصادر والمراجع 📜
//
//  قرار المستخدم: توثيق المصدر **في القائمة فقط** — لا سطر مصدر على شاشة العدّاد.
//  أذكار المجموعات الأربع (بعد الصلاة · الصباح · المساء · النوم) مطابقة لفصول
//  كتاب «حصن المسلم» نصًّا وعددًا؛ والنصوص كلها من الموقع الرسمي للكتاب.

struct SourcesView: View {

    private struct SourceRow: Identifiable {
        let id = UUID()
        let icon: String
        let title: String
        let body: String
    }

    private let rows: [SourceRow] = [
        SourceRow(icon: "book.closed.fill", title: "«حِصْنُ الْمُسْلِم»",
                  body: "من أذكار الكتاب والسنة — د. سعيد بن علي بن وهف القحطاني، الرياض."),
        SourceRow(icon: "link", title: "المصدر الرسمي",
                  body: "hisnmuslim.com — منه أُخذت نصوص الأذكار وأعدادها."),
        SourceRow(icon: "books.vertical.fill", title: "المطابقة",
                  body: "أذكار بعد الصلاة · الصباح · المساء · النوم = فصول الكتاب الأربعة، بالصيغة والعدد الوارد فيها."),
        SourceRow(icon: "sparkles", title: "المجموعات الأخرى",
                  body: "متنوعة · الاستغفار · الصلاة على النبي ﷺ · تسبيح مفتوح — أذكار ثابتة مشهورة."),
    ]

    var body: some View {
        ScrollView {
            VStack(spacing: 8) {
                ForEach(rows) { row in
                    VStack(alignment: .leading, spacing: 4) {
                        HStack(spacing: 5) {
                            Image(systemName: row.icon)
                                .font(.system(size: 10, weight: .semibold))
                                .foregroundStyle(SabhaColor.emerald)
                            Text(row.title)
                                .font(SabhaFont.ui(11, weight: .semibold))
                        }
                        Text(row.body)
                            .font(SabhaFont.ui(10))
                            .foregroundStyle(.secondary)
                            .fixedSize(horizontal: false, vertical: true)
                            .multilineTextAlignment(.leading)
                    }
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .sabhaCard(padding: 9)
                }

                Text("النص الكامل لكل ذكر يظهر في وضع القراءة · التطبيق يعمل بلا إنترنت · وعند أي اختلاف يُرجَع إلى الكتاب نفسه.")
                    .font(SabhaFont.ui(9))
                    .foregroundStyle(.tertiary)
                    .multilineTextAlignment(.center)
                    .padding(.horizontal, 6)
            }
            .padding(.horizontal, 4)
            .padding(.bottom, 8)
        }
        .sabhaScreenBackground()
        .navigationTitle("المصادر")
    }
}

// MARK: - رسالة إتمام المجموعة 🎉

struct CompletionView: View {

    let summary: SessionSummary
    var onRestart: () -> Void
    /// 🏠 الرجوع إلى الشاشة الرئيسية (أيقونات الأذكار)
    var onHome: () -> Void
    var onClose: () -> Void

    @State private var pulse = false

    var body: some View {
        ZStack {
            Color.black.opacity(0.96).ignoresSafeArea()

            ScrollView {
                VStack(spacing: 8) {

                    Image(systemName: "checkmark.seal.fill")
                        .font(.system(size: 38))
                        .foregroundStyle(.green)
                        .scaleEffect(pulse ? 1.08 : 1.0)
                        .animation(.easeInOut(duration: 0.9).repeatForever(autoreverses: true), value: pulse)

                    Text(summary.closeTitle)
                        .font(.system(size: 15, weight: .bold, design: .rounded))
                        .multilineTextAlignment(.center)

                    Text(summary.closeDua)
                        .font(.system(size: 11))
                        .foregroundStyle(.secondary)
                        .multilineTextAlignment(.center)
                        .padding(.bottom, 2)

                    // ملخّص الجلسة — ثلاث خلايا متساوية (اسم المجموعة في العنوان أعلاه، فلا تكرار)
                    HStack(spacing: 6) {
                        cell("\(summary.dhikrCount)", "أذكار")
                        cell("\(summary.totalTaps)", "ضغطة")
                        cell(summary.durationText, "المدة")
                    }
                    .padding(.vertical, 2)

                    VStack(spacing: 6) {
                        Button(action: onRestart) {
                            Label("إعادة المجموعة", systemImage: "arrow.counterclockwise")
                                .font(.system(size: 12, weight: .semibold))
                                .frame(maxWidth: .infinity)
                        }
                        .buttonStyle(.borderedProminent).tint(.teal)

                        Button(action: onHome) {
                            Label("الشاشة الرئيسية", systemImage: "house")
                                .font(.system(size: 12))
                                .frame(maxWidth: .infinity)
                        }
                        .buttonStyle(.bordered)

                        Button("إغلاق", action: onClose)
                            .font(.system(size: 11))
                            .foregroundStyle(.secondary)
                    }
                    .padding(.top, 2)
                }
                .padding(.horizontal, 12)
                .padding(.vertical, 6)
            }
        }
        .onAppear { pulse = true }
    }

    /// خلية ملخّص: الرقم كبير فوق، والتسمية صغيرة تحته — بلا التفاف ولا كلمات مبعثرة
    private func cell(_ value: String, _ label: String) -> some View {
        VStack(spacing: 1) {
            Text(value)
                .font(.system(size: 13, weight: .bold, design: .rounded))
                .lineLimit(1)
                .minimumScaleFactor(0.6)
            Text(label)
                .font(.system(size: 8.5))
                .foregroundStyle(.secondary)
                .lineLimit(1)
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, 6)
        .background(.white.opacity(0.07), in: RoundedRectangle(cornerRadius: 10))
        .overlay(RoundedRectangle(cornerRadius: 10).stroke(.white.opacity(0.09), lineWidth: 0.7))
    }
}
